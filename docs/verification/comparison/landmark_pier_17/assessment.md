# Pier 17, South Street Seaport

`landmark_pier_17` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Lower Manhattan Skyline September 2021.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2021-09-10 12:49:26, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Lower_Manhattan_Skyline_September_2021.jpg) — the photograph's own view direction is derived from the image at **high** confidence. **The file names what it is: a skyline.** It shows the Financial District's towers over the FDR viaduct, with a deep blue September sky and cumulus. Pier 17 is not in it.

**Camera** — 40.705667, -74.002747 (NYC_TM -4458, 631) at z 4.2 m NAVD88 | azimuth 59.7°, pitch 0.0° | 35 mm on 36 mm (54.4° horizontal, landscape) | 1208x906. The camera stands on **this photograph's own EXIF GPS**, **130.4 m** from the item's recorded viewpoint; the item's recorded azimuth is 120.0°, **60.3° away**, and belongs to the nominal viewpoint. The walk **did not move it**: the view azimuth is clear for **150.0 m** against a **36.6 m** requirement, the nearest built thing in the frame is **`t_-5_0_struct_pier_deck` 4.4 m** away — the tile's pier-deck structures joined into one object (J94) — and no simulated agent stands within 60 m. The ground under it reads 2.628 m NAVD88 from the 2 m heightmap, 16 samples within 5 m, range 2.63 to 2.63 m.

**Sun** — azimuth 178.6°, elevation 54.0° at 2021-09-10T12:49:26−04:00, from the photograph's own **EXIF DateTimeOriginal**; 901.7 W/m² direct normal, sky at strength 0.0316, Filmic, **+0.95 stops** metered and unclamped, against a linear median of **0.093455** and a target of **0.18**. The physical rule would have given **0.0 stops**.

**In the scene** — 4,500,060 triangles: 6 building tiles (138,524 tris, 0 missing, 0 LOD-substituted), 6 landmark models of which 2 can fall inside the 54.4° frame, 14,065 pavement polygons, 1,254 props, 7,550 kit pieces, 27 park-ground meshes over 450 surfaces, **106,520 triangles of structures** over 5 tiles, 89 vehicles and 432 people.

## Verdict — no sightline was tested at all, because the thing standing at Pier 17's coordinate is one metre tall

**The probe found the pier, not the building.** It cast 43 rays, landed **43 of 43** on built fabric, and reported the highest built thing at the subject's coordinate as `lm_c_pier_17_seaport.3` at z **3.66 m** over a ground of **2.63 m** — **1.0 m** up. The record's own words: *below the 2 m at which a subject has a height worth aiming or framing by*. So the lens was **not widened**, the optical axis was left **level** because the subject's mid-height is not known, and **no sightline was tested**: this sheet carries no `subject_visible_fraction` of any kind. It is one of the seven sheets in that condition (J96), and the cause here is plain from the catalogue — `c_pier_17_seaport` is a **20.7 m** entry whose origin stands **64.0 m** from the coordinate the item records, so the coordinate sits out on the deck and the shed is elsewhere on the pier (J94).

**The frustum then puts the subject at the frame's edge.** Pier 17 is reported **101.0 m** away at **39.5° off axis** in a **54.4°** frame, so at best its near corner grazes the right-hand border. The render bears that out: a glazed shed with dark mullions and a timber deck runs off the right edge, and the rest of the frame is a Seaport street corner — a brick building at close range, the FDR viaduct behind, and a wide pale plaza across the bottom half.

**And the reference is a different picture entirely.** The photograph's own filename says *Lower Manhattan Skyline September 2021*, and that is what it is: the Financial District's towers, one still in construction scaffolding, the Woolworth spire, a deep blue sky and cumulus, and the FDR viaduct across the bottom. Nothing in it is Pier 17. The camera is on that photograph's GPS and its heading is the bearing to Pier 17, which is **60.3°** from the item's own recorded azimuth — so the render looks at the pier and the photograph looks at the skyline from the same spot. Two true views, ninety degrees apart in subject.

**The one thing this sheet does establish, and it is not trivial.** With the development metered, the two halves agree on tone more closely than almost any pair in the pass: p50 **0.4949** against **0.4773**, a ratio of **1.037**; mean **1.071×**; standard deviation **0.2094** against **0.2409**, **0.869×**. The photograph's own median sits only **0.106 stops** from the grey convention and the render's **0.218**, a **+0.112-stop** difference. Two unrelated views of the same block in the same light come out at the same exposure, which is what J83's metered development was built to do.

## What matches

* **The tone and the contrast** — p50 1.037, mean 1.071, sd 0.869, and the two exposures within an eighth of a stop of each other (J83).
* **The waterfront is built as structures, heavily** — **106,520 triangles** over 5 tiles, the largest structures figure on any sheet written so far, on a stretch that is piers, the FDR viaduct and a seawall.
* **The probe found fabric on 43 of 43 rays** and reported honestly what it found, including that it was too low to frame by.
* **The Seaport is furnished as the Seaport** — **183 benches**, 279 Citi Bike units, 131 street lamps, 104 manholes, 68 hydrants, 66 cooling towers, **47 waste baskets**, **8 flagpoles**, 3 bus shelters, 2 newsstands.
* **The park ground is exact near the camera** — within 150 m, 72 samples, an under-fraction of **0.0**, a median clearance of **0.204 m** and no z-fighting; between 150 and 400 m the under-fraction is **0.012** over 83 samples, the best mid-field reading on any sheet written so far.
* **The camera did not have to be walked** — 150 m of clear view against a 36.6 m requirement.
* **14,065 pavement polygons and none dropped**, including **950 plaza** polygons, which is what a seaport promenade is made of.

## What does not match

* **The reference is a skyline photograph and the item is a pier building.** The two frames share a viewpoint and nothing else.
* **No sightline exists on this sheet.** The subject's coordinate carries a 1.0 m object, so nothing was aimed, framed or ray-tested against it (J96).
* **The subject is 39.5° off axis in a 54.4° frame** — at the border, not in the picture (J88).
* **The catalogue and the coordinate disagree by 64 m.** `c_pier_17_seaport` is 20.7 m tall and its origin stands 64.0 m from the point the item records (J94).
* **A tile mesh is the nearest thing in the frame.** `t_-5_0_struct_pier_deck` at 4.4 m is every pier-deck structure in that tile joined into one object (J94).
* **A quarter of the photograph's colour** — chroma **0.0506** against **0.1807**, a ratio of **0.280**. The reference's deep blue September sky and its cumulus are most of that, and nothing in this build reads a historical sky.
* **The Financial District towers in the photograph's middle distance have no counterpart** in a frame pointed at a pier.
* **Props were capped to under half** — **1,254 of 2,825 in range** at a **1,217,049-triangle** budget, **1,382 dropped for budget**, **999** of them tree rows, and **238** of the 318 trees drawn are a substituted species.
* **Kit was capped to under half** — **7,550 of 16,968 in range** at a **1,176,762-triangle** budget, 6,721 of them windows, with **158** suppressed under landmark shells; the openings are not cut (Stage 34 / J51).
* **One of five tiles in range has no structures file.**
* **22 props across seven kinds in range have no asset** — **8 drinking fountains**, 3 memorials, 3 misc structures, 2 artworks, 2 parks comfort stations, 2 vending machines, 1 parks building.
* **384 pedestrians were dropped for standing in the carriageway without crossing and 177 for standing off a walkable surface** — on a waterfront whose promenade and plaza are exactly the surfaces the crowd's walkable test cannot see (J101). **2,060 agents dropped** in total, against 432 people and 89 vehicles drawn.
* **Nine park surface kinds keep the builder's flat colour** — infield clay, cemetery grass, hard sport court, greenstreet grass, park grass, pool water, recreation grass, **polyurethane running track** and bare ground (J40).
* **Beyond 400 m the park ground reads under the terrain on 0.2947 of 621 samples**, worst **−3.626 m**, z-fighting **0.0258**. The redrape moved **256,026** vertices, up to 1.404 m up and 1.656 m down.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the reference is a skyline, not the pier | the chooser accepted a photograph whose own filename says *Lower Manhattan Skyline*; it is a true photograph from the recorded neighbourhood and not a photograph of the subject | **verification — open, the pairing is the fault** |
| no sightline was tested | the object standing at the subject's coordinate is 1.0 m tall, below the 2 m at which the probe will aim or frame, so the sightline was skipped (J96) | verification — declared, and the coordinate is the fault |
| the coordinate is 64 m from the catalogue origin of a 20.7 m entry | the item's recorded point sits on the pier deck rather than on the shed (J94, J96) | **data — open, the coordinate** |
| the subject is 39.5° off axis | the heading is the bearing from the photograph's GPS to the subject, and the frustum's own footprint centroid puts it at the frame border (J88) | verification |
| a joined tile mesh 4.4 m from the lens | `t_-5_0_struct_pier_deck` is one tile's pier-deck structures joined into a single object (J94) | geometry — open |
| chroma 0.280 | a deep blue September sky with cumulus against a clear-sky render; nothing in this build reads a historical sky | reference — no source exists |
| 1,254 props of 2,825, 999 tree rows dropped | the props triangle budget at 1,217,049 | performance |
| 7,550 kit pieces of 16,968 | the kit triangle budget at 1,176,762 | performance |
| windows drawn on the shell | Stage 34 / J51, measured at +48 GB | declared decision — physically impossible here |
| 177 pedestrians off a walkable surface on a promenade | the crowd's walkable test reads only the road network's sidewalk, median, plaza and crosswalk, and a boardwalk or pier deck is not a surface class (J101) | **verification — open (J101)** |
| one of five tiles without a structures file | that tile is unbuilt | data — open |
| 22 props across seven kinds unmapped | no asset exists for those kinds | data |
| nine park surface kinds flat | the texture catalogue has no photographic set for clay, grass, court, pool water, running track or bare ground (J40) | data — declared, named on the sheet |
| under-fraction 0.2947 beyond 400 m | the terrain grid coarsens to 40 m at the scene edge and the park builder drapes on its own heightmap; the redrape closes the near and mid field and leaves this tail (J71) | geometry — open, bounded |
| 432 people of 1,667 asked | the placement rules and the agent triangle budget, each with its own count | performance + verification |
