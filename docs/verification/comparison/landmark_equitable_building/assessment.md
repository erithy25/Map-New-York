# Equitable Building (120 Broadway)

`landmark_equitable_building` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Equitable Building April 2022 001.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-04-01 13:09:11, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Equitable_Building_April_2022_001.jpg) — the photograph's own view direction is derived from the image at **high** confidence. It is the **H-plan slab** looking up from the Broadway sidewalk: two wings flanking a deep re-entrant light court, the window grid stepping away in perspective, the rusticated base with its carved panels and bronze band, a projecting cornice line, a flagpole, and a wedge of blue sky in the notch.

**Camera** — 40.708686, -74.011078 (NYC_TM -5163, 953) at z 12.2 m NAVD88 | azimuth 120.1°, pitch +32.0° | 18 mm on 36 mm (90.0° horizontal, 74° vertical, landscape) | 1208x906. The camera stands on **this photograph's own EXIF GPS**, **45.1 m** from the item's recorded viewpoint; the item's recorded azimuth is 85.0°, **35.1° away**. The lens was held at the **18 mm floor** and the record states the top of the subject is still cut off and the verticals converge. The walk then **moved it 12.4 m** onto the nearest surveyed crosswalk polygon, the recorded viewpoint being boxed in at **22 m** against the **39.1 m** the frame needs. From there the view is clear for **40.7 m**, the nearest built thing is `prop_lamp_cobra_davit_5` **12.3 m** away, and the nearest simulated agent a for-hire vehicle **9.6 m** out, measured after the cull over the observer. The ground reads 10.638 m NAVD88, the 10th percentile of 113 samples within 12 m, range 10.26 to 11.26 m.

**Sun** — azimuth 184.0°, elevation 54.0° at 2022-04-01T13:09:11−04:00, from the photograph's own **EXIF DateTimeOriginal**; 901.7 W/m² direct normal, sky at strength 0.0316, Filmic, **+6.00 stops** — **clamped** from a wanted **6.78**. The physical rule would have given **0.0 stops**. A 54° Sun almost due south, into a light court between two wings on Broadway, is a well at noon.

**In the scene** — 4,500,140 triangles: 4 building tiles (106,490 tris, 0 missing, 0 LOD-substituted), 12 landmark models of which 4 can fall inside the 90.0° frame, 22,921 pavement polygons, 913 props, 3,221 kit pieces, 19 park-ground meshes, 43,576 triangles of structures, 50 vehicles and 252 people.

## Verdict — the closest height agreement in the pass, on the best-matched massing in it

**Eight centimetres.** The probe measured **164.68 m** above a ground of 10.89 m against the catalogue's **164.6 m** for `equitable_building`, whose origin stands **23.1 m** from the coordinate. That is the closest probe-to-catalogue agreement written up so far, ahead of the Plaza Hotel's 0.13 m. **35 of 43** rays found fabric — eight passed up through the light court, which is what a fan aimed at a notched slab should do.

**And the massing is the best match in the pass.** The render carries the H-plan: two brick wings, the deep re-entrant court between them running the full height, the same window rhythm, the same convergence, the same dark slot of shadow in the notch. Put the two halves side by side and the plan form, the proportion of wing to court, and the window grid all correspond. The plan extent, **103.9 m by 102.5 m**, is the building's own footprint. Of thirteen sightline rays **12 are clear** and **11 land on the subject** — a visible fraction of **0.846** — and what blocks the thirteenth is `lm_equitable_building.8`, one of its own wings, at 24.7 m.

**The tone agrees too, without help.** Mean **0.902**, p50 **0.94**, and the photograph's median sitting **0.29 stops below** the grey convention against the render's **0.479 below** — a difference of only **−0.189 stops**, on a frame the meter had to lift by **6.00 clamped stops** from a wanted 6.78. Both halves are dark because a light court at noon is dark.

**What is missing is the relief.** The rusticated base, the carved spandrel panels, the bronze band at the ground floor and the projecting cornice line are all absent; the render's base is plain brick and its cornice is a shadow rather than a profile. The kit numbers say why: **3,221 pieces drawn of 27,102 in range** at a **1,072,570-triangle** budget, of which **2,983 are windows** and the ornament is **20 cornices, 20 string courses, 15 window accessories, 14 pilasters**. Chroma **0.664** and contrast **0.817** follow from the same thing.

**One figure on this sheet is unlike any other.** `parkground.faces_cut_for_landmark_ground` reads **53,345** — two orders of magnitude above the next largest in the pass. Twelve landmark models stand in this radius, four of them in frame, and every one of their ground plates is cut out of the park ground beneath. It is not a fault; it is the measure of how dense Lower Manhattan's landmark set is.

## What matches

* **The height, to 0.08 m** — 164.68 m measured against a catalogued 164.6 m from an origin 23.1 m away.
* **The H-plan massing** — two wings, the full-height light court, the window rhythm and the convergence.
* **The plan extent** — 103.9 m by 102.5 m, measured off the model.
* **The sightline** — 12 of 13 rays clear, 11 on the subject, and the one that is blocked is blocked by the building's own wing.
* **The tone** — mean 0.902, p50 0.94, exposure difference **−0.189 stops**, on a +6.00-stop clamped frame.
* **Eight of 43 probe rays pass up through the light court**, which is the correct answer for a notched slab.
* **The Financial District is furnished** — **263 Citi Bike units**, 107 street lamps, 83 manholes, 63 cooling towers, 57 hydrants, 46 subway vent grates, **23 subway entrances**, 20 waste baskets, 17 bus-stop signs, 4 flagpoles.
* **22,921 pavement polygons and none dropped**, including **1,299 plaza** and 660 crosswalk.
* **The frustum names four landmarks in the frame** — the Equitable at 62.0 m, Federal Hall at 154.6 m, 40 Wall Street at 207.4 m and the Brooklyn Bridge at 1,287.6 m.

## What does not match

* **No rustication, no carved panels, no bronze band, no cornice profile.** The base is plain brick and the cornice is a shadow line.
* **No flagpole on the facade**, where the photograph has one on the court's axis.
* **Published at the +6.00-stop clamp** from a wanted 6.78 (J83).
* **Two thirds of the photograph's colour** — chroma **0.664** — and **0.817** of its contrast.
* **Kit was capped to one piece in eight** — **3,221 of 27,102 in range** at a **1,072,570-triangle** budget, with **1,760** further pieces suppressed under landmark shells; the openings are drawn rather than cut (Stage 34 / J51).
* **Props were capped to under a quarter** — **913 placed of 3,971 in range** at a **1,161,491-triangle** budget, **2,813 dropped for budget**, **2,185** of them tree rows, and only **110** trees are drawn from modelled branches against 79 impostor cards; 16 were dropped on a suppressed building.
* **22 props across three kinds in range have no asset** — **11 artworks**, **9 memorials**, 2 drinking fountains. In Lower Manhattan those are the memorials that matter.
* **One of four structure tiles has no file**, although **43,576 triangles** came from the three that do.
* **Beyond 400 m the park ground reads under the terrain on 0.3353 of 683 samples**, worst **−3.165 m**; between 150 and 400 m it is **0.102** over 451 samples.
* **3,344 agents were dropped** — 1,204 pedestrians at the agent triangle budget, **291 in the carriageway without crossing**, 175 vehicles at the budget, **152 where the planimetric data has no sidewalk** (J101), 6 cyclists the fleet exports without a rider.
* **No cloud.** The reference's sky is a clear April blue in the notch; nothing in this build reads a historical sky.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no rustication, carved panels, bronze band or cornice profile | the kit budget placed 2,983 windows and 69 ornamental pieces of 27,102 in range, and rustication, carved spandrels and a bronze band are not classes this build models | **performance + geometry — the largest fidelity gap on this sheet** |
| no flagpole on the facade | 4 flagpoles are placed in the scene but a facade-mounted staff is not a class the kit carries | geometry |
| published at the +6.00 clamp | a light court between two wings at a 54° Sun is a well at noon; the development is metered on it (J83) | verification — declared, and correct |
| chroma 0.664, sd 0.817 | flat brick against rusticated stone, carved panels and a bronze band | geometry |
| 3,221 kit pieces of 27,102, 1,760 more suppressed | the kit triangle budget at 1,072,570, plus the landmark shell replacing the tile's buildings | performance + declared decision |
| 913 props of 3,971, 2,185 tree rows dropped | the props triangle budget at 1,161,491 | performance |
| openings drawn on the shell | Stage 34 / J51, measured at +48 GB | declared decision — physically impossible here |
| 22 props across three kinds unmapped, 11 artworks and 9 memorials | no asset exists for those kinds | **data — open, and Lower Manhattan is where it shows** |
| one of four structure tiles without a file | that tile is unbuilt | data — open |
| a 0.3353 far-field under-fraction | the park builder drapes on its own heightmap and the scene's coarsens at the edge (J71) | geometry — open, bounded |
| 252 people of 4,456 asked | the agent triangle budget plus the placement rules, each with its own count | performance + verification |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
