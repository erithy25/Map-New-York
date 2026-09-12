# Ed Koch Queensboro Bridge

`landmark_queensboro_bridge` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Ed Koch Queensboro Bridge, New York City, 20231001 1106 1018.jpg by Jakub Hałun, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0), taken 2023-10-01 11:06:20, 1920x2254. [Commons page](https://commons.wikimedia.org/wiki/File:Ed_Koch_Queensboro_Bridge,_New_York_City,_20231001_1106_1018.jpg) — the photograph's own view direction is derived from the image at **high** confidence. Taken from Sutton Place Park looking east along the span: the cantilever truss in its buff-and-red paint, the Con Edison smokestack behind it, brick apartment blocks at the left, a green-glass tower on the far bank, and the East River **choppy and olive-green** across the bottom third.

**Camera** — 40.757164, -73.957833 (NYC_TM -661, 6348) at z 1.6 m NAVD88 | azimuth 102.8°, pitch 0.0° | 35 mm on 36 mm (47.3° horizontal, 54.4° vertical, portrait) | 964x1132. The camera stands on **this photograph's own EXIF GPS**, **173.0 m** from the item's recorded viewpoint, and its heading agrees with the item's recorded 104.1° to **1.3°**. The axis was left **level** because the subject is 332 m off. The walk **did not move it**: the view azimuth is clear for **150.0 m** against an **80.0 m** requirement, **nothing built stands within 60 m** and no simulated agent within 60 m. **The ground under it reads 0.0 m NAVD88** — point sample 0.0, minimum 0.0, median 0.0, maximum 0.0 over **113 samples within 12 m** — so the eye sits **1.6 m above the tidal datum**, which is the level the hydrography flattens every tidal body to (`TIDAL_Z_M = 0.0` in `terrain/hydro.py`).

**Sun** — azimuth 146.6°, elevation 40.5° at 2023-10-01T11:06:20−04:00, from the photograph's own **EXIF DateTimeOriginal**; 844.5 W/m² direct normal, sky at strength 0.0334, Filmic, **+1.23 stops** metered and unclamped against a linear median of **0.076829** and a target of **0.18**. The physical rule would have given **0.09 stops**.

**In the scene** — 4,500,007 triangles: 9 building tiles (298,094 tris, 0 missing, 0 LOD-substituted), 7 landmark models of which 1 can fall inside the 47.3° frame, 20,253 pavement polygons, 1,210 props, 6,774 kit pieces, 22 park-ground meshes, 88 vehicles and 303 people.

## Verdict — the bridge is unmistakable and the camera is standing in the river

**This is one of the best identifications in the pass.** The cantilever truss sweeps out of the top-left corner across the frame exactly as it does in the photograph, with the same chord curve, the same web rhythm, the same deep plate girder under the deck and the same massive pier. The probe found fabric on **43 of 43 rays** and measured **66.02 m** above a ground of 5.68 m on `lm_b_queensboro_bridge.96`, whose plan extent is **1002.4 m by 588.0 m** — the whole bridge as a single member, so the extent is the structure's and not a part's. The catalogue's **106.68 m** for `b_queensboro_bridge` is the tower and the probe measured the truss at the coordinate, which is the right answer to a different question (J74, J94). The frustum puts the bridge **5.7° off axis** at 289.2 m and the heading agrees with the recorded one to **1.3°**.

**And the eye is 1.6 m above the water.** Every one of the 113 heightmap samples within 12 m of the camera reads **0.0 m NAVD88**, the tidal datum, so the viewpoint sits on the flattened East River surface rather than on Sutton Place Park's terrace above the FDR Drive. The consequence is the whole lower half of the render: a mirror-flat reflection of the bridge from a lens almost at water level, where the photograph looks **down** on choppy water from a park several metres up. Whether the photograph's GPS fix falls a few metres offshore or the heightmap is wrong at the bank, this record cannot say — what it can say is that all 113 samples agree. **Seven sheets in the pass stand at exactly 0.0 m this way**, every one of them a waterfront or on-water viewpoint (J103).

**The water is a mirror and the river is not.** The render's East River is a flat specular plane that returns a clean inverted image of the truss. The photograph's is wind-roughened, olive-green with sediment, and returns nothing. Nothing in this build gives open water a wave state or a turbidity, and at this eye height that gap occupies more of the frame than any other single difference.

**The paint is missing.** The photograph's truss is buff with red-brown members — the bridge's own livery, and the reason it reads warm against a blue sky. The render's is pale neutral grey. Measured: chroma **0.0968** against **0.1681**, a ratio of **0.576**.

## What matches

* **The truss.** Chord curve, web rhythm, deck girder and pier are all in the render in the right proportions, at the right bearing and the right distance.
* **The height and the aim** — 66.02 m on **43 of 43** probe rays; recorded azimuth against measured bearing at **1.3°**; the frustum at **5.7° off axis**, 289.2 m.
* **The plan extent is the structure's own** — 1002.4 m by 588.0 m, measured off the model rather than a catalogue row.
* **The far bank is right in kind** — brick apartment blocks, a glass tower, trees and a street with cars, which is what Long Island City's shore shows from here.
* **The camera did not have to be walked** — 150 m clear against an 80 m requirement, nothing built within 60 m.
* **All nine building tiles in range are complete** — 298,094 triangles, **0 missing**, **0 LOD-substituted**.
* **20,253 pavement polygons and none dropped**, including 10,755 white markings and 433 crosswalk.

## What does not match

* **The camera stands at the tidal datum**, 1.6 m above the water, instead of on the park terrace the photograph was taken from (J103).
* **The water is a mirror.** No wave state, no turbidity; the render returns a clean reflection where the river returns none.
* **The bridge's buff-and-red paint is absent** — chroma **0.576** of the photograph's.
* **The Con Edison smokestack is not in the frame**, where the photograph has it as the tallest thing behind the truss.
* **The render is brighter at the midtone and flatter** — p50 **0.4977** against **0.364**, a ratio of **1.367**, mean **1.28×**, sd **0.1551** against **0.1917** (**0.809×**). The photograph's median sits **0.723 stops below** the grey convention and the render's **0.235 above**, a **+0.958-stop** difference (J83).
* **The visible fraction is 0.231** — of 13 rays, **7 are clear**, **3 land on the subject**, 3 pass into open sky, and the rest stop at **185.7 m** on `t_-1_6_brown_brick`, one tile's brown-brick surfaces joined into a single object (J94).
* **Not one tree is drawn from modelled branches** — **0** at LOD0, 490 as impostor cards, and **3,535 tree rows did not fit** the props budget.
* **Props were capped to one in four** — **1,210 placed of 4,939 in range** at a **1,208,931-triangle** budget.
* **Kit was capped to under half** — **6,774 of 16,172 in range** at a **1,336,393-triangle** budget; the openings are not cut (Stage 34 / J51).
* **No park ground was built for three tiles in range** — `t_-1_5`, `t_0_5`, `t_0_6` — so there is bare terrain there (J102).
* **12 props across six kinds in range have no asset** — 3 artworks, 2 drinking fountains, 2 misc structures, 2 parks buildings, 2 real-time information signs, 1 parks comfort station.
* **3,080 agents were dropped** — **875 pedestrians in the carriageway without crossing**, 355 where the planimetric data has no sidewalk (J101), 155 vehicles at the agent triangle budget, 30 cyclists and e-bikes the fleet exports without a rider, 8 vehicles where there is no roadway.
* **No cloud.** The reference's sky is a clear deep October blue that the Nishita sky does not reach; nothing in this build reads a historical sky.
* **Six park surface kinds keep the builder's flat colour** — hard sport court, field grass, park grass, recreation grass, rink ice and bare ground (J40).

## Measured for this assessment

| figure | how |
|---|---|
| seven sheets in the pass stand at exactly 0.0 m NAVD88 | read `camera.terrain_z_m` out of every record carrying `scene.structures`: the Brooklyn Bridge walkway, Domino Park, Ellis Island, Hell Gate Bridge, this sheet, the RFK Triborough Bridge and the Staten Island ferry frame; no camera in the pass sits between 0.0 and 0.5 m, so the set is exactly the ones on the flattened tidal surface |
| the tidal datum is 0.0 m NAVD88 | `TIDAL_Z_M = 0.0` in `pipeline/nycsim_pipeline/terrain/hydro.py`, which flattens every tidal body to it |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the camera stands 1.6 m above the water | all 113 heightmap samples within 12 m of the photograph's own GPS read 0.0 m, the tidal datum every tidal body is flattened to; the viewpoint is on or inside the flattened water surface rather than on the park above it (J103) | **geometry — open (J103), 7 sheets** |
| the water is a mirror | open water is a flat specular plane with no wave state and no turbidity | geometry — open, and it fills half this frame |
| the truss has no paint | the bridge model carries the material palette's neutral steel and no livery colour | geometry |
| chroma 0.576, p50 1.367, sd 0.809 | the missing paint, the mirror water, and a photograph developed 0.723 stops below the grey convention against a render 0.235 above it (J83) | geometry + reference |
| no Con Edison smokestack | it stands outside this frame from the photograph's own GPS | verification — the pairing |
| the visible fraction is 0.231 | six of thirteen rays are stopped at 185.7 m by one tile's brown-brick surfaces joined into a single object (J94) | geometry — open |
| 0 trees from modelled branches, 3,535 tree rows dropped | the props triangle budget at 1,208,931 | performance |
| 6,774 kit pieces of 16,172 | the kit triangle budget at 1,336,393 | performance |
| windows drawn on the shell | Stage 34 / J51, measured at +48 GB | declared decision — physically impossible here |
| no park ground for three tiles | 85 % of the city's mapped open space has no ground geometry, and these three tiles are among those never draped (J102) | data — open (J102) |
| 12 props across six kinds unmapped | no asset exists for those kinds | data |
| 875 pedestrians in the carriageway, 355 off a walkable surface | the crowd model puts walkers on surfaces the placement test reads as roadway or cannot read at all (J101) | verification — open (J101) |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
| six park surface kinds flat | the texture catalogue has no photographic set for court, grass, ice or bare ground (J40) | data — declared, named on the sheet |
