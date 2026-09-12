# Metropolitan Museum of Art

`landmark_metropolitan_museum` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Metropolitan Museum of Art (The Met) - Central Park, NYC.jpg by Hugo Schneider, CC BY-SA 2.0 (https://creativecommons.org/licenses/by-sa/2.0), taken 2019-09-09 13:46:08, 1920x1072. [Commons page](https://commons.wikimedia.org/wiki/File:Metropolitan_Museum_of_Art_(The_Met)_-_Central_Park_NYC.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.77892, -73.962215 (NYC_TM -1031, 8764) at z 27.6 m NAVD88 | azimuth 302.7°, pitch +0.2° | 30 mm on 36 mm (62.7° horizontal, 38° vertical, landscape) | 1280x714. The camera stands on **this photograph's own EXIF GPS**, **2.6 m** from the item's recorded viewpoint — the closest agreement between a photograph and an item in this pass — and the bearing it takes to the subject, 302.7°, is **0.7°** from the item's recorded 303.4°. The walk **did not move it**: the view azimuth is clear for **123.0 m** against a **49.4 m** requirement, the nearest built thing in the frame is `lm_b_central_park_walls_gates.2` **19.5 m** away and the nearest simulated agent `agent_ped_2134.0` **20.4 m** away against a **60.0 m** probe. The lens was widened from 35 mm to 30 mm so that a level axis contains the subject. The ground under it reads 25.962 m NAVD88 from the 2 m heightmap, 16 samples within 5 m, range 25.9 to 26.02 m; the viewpoint note names the raised surface the photographer stood on, so the point's own height is used rather than a percentile (J65).

**Sun** — azimuth 202.0°, elevation 52.5° at 2019-09-09T13:46:08−04:00, from the photograph's own **EXIF DateTimeOriginal**; 897.0 W/m² direct normal, sky at strength 0.0317, Filmic, **+3.06 stops** metered and unclamped, against a linear median of **0.021555** and a target of **0.18**. The physical rule would have given **0.0 stops**. A 52.5° Sun almost due south at 13:46, against a facade that faces east: the real facade is in its own shade at this hour, and the photograph shows exactly that.

**In the scene** — 4,500,117 triangles: 4 building tiles (284,244 tris, 0 missing, 0 LOD-substituted), 4 landmark models of which 2 can fall inside the 62.7° frame, 16,565 pavement polygons, 758 props, 4,096 kit pieces, 13 park-ground meshes over 451 surfaces, 2,364 triangles of structures, 73 vehicles and 255 people.

## Verdict — the item names the Fifth Avenue facade, the model carries it at 69,436 triangles, and the builder put it on the Central Park side

**The render shows the back of the museum.** The right-hand frame is a plain limestone mass filling the whole upper half, with a single row of small blocks along one edge, a dark soffit shadow beneath it, a pale unarticulated surface below that, and then pavement with a black sedan, a yellow taxi and a line of standing figures. No arches, no paired columns, no pediment, no cornice, no grand stair, no banners, no sky. The photograph is the Fifth Avenue front: three giant round arches, the McKim colonnades either side, the balustraded attic, the stair full of people.

**This is not a missing model. It is a model facing the wrong way, and the builder says so in its own words.** `blender/landmarks/c_metropolitan_museum.py` opens with the premise *"Fifth Avenue is west (local −x); Central Park is east"*, and both of its elevation tests follow it: the colonnade is applied to the faces whose outward normal points **west** (`if float(n[0]) > -0.4 ... continue`, commented *"only the Fifth Avenue (west) elevation"*) and the Roche Dinkeloo glass slopes to the faces pointing **east** (commented *"only the east (Central Park) faces"*). In New York it is the other way round: the Met stands on the **east** edge of Central Park and Fifth Avenue runs along its **east** side. This project's own coordinates settle it without appeal to anything else — the catalogue puts the model's origin at NYC_TM (−1134.0, 8821.0) and this camera, standing on Fifth Avenue on the photograph's own GPS, is at (−1031, 8764), which is **103 m east** of that origin. The catalogue's placement rule is *"translate the model to origin_tm; apply no rotation. The model axes are already parallel to NYC_TM"*, so local +x **is** east, and the two articulated elevations are on the far side from the avenue they are named after.

**The cost, in triangles.** Measured off `blender_out/landmarks/c_metropolitan_museum.glb`: the colonnade carries **69,436** triangles and the central pavilion with its arches and its grand stair **12,941** — together **82,377 of the model's 84,671** triangles outside its LOD1 — and both sit at local x below −8.7, west of the origin. What faces the camera instead is `c_metropolitan_museum_rear`, **280 triangles**, 262.5 m by 322.8 m in plan, from 9 to 26.8 m of model height, and the base core below it at **368 triangles**. The record names the first of those as the object it measured: `probe.object` is `lm_c_metropolitan_museum.6` and its recorded plan extent, **322.8 m by 262.5 m**, is that mass's bounding box to the decimal. So the height, the lens and the pitch on this sheet were all set from the back wall.

**Everything the verification did with that mass, it did correctly.** 43 of 43 probe rays found fabric, at **30.22 m** above a ground of 27.06 m, against the catalogue's **42.0 m** for `c_metropolitan_museum` whose origin stands 20.1 m away — and 30.22 m is a fair reading of a 26.8 m mass on a raised base. 11 of 13 sightline rays are clear and **11 land on the subject**, a visible fraction of **0.846**, one of the highest in the pass; **all 11** land on the museum's own fabric at **45.9 m**, less than half the 98.8 m to the coordinate, which the record states as `subject_rays_on_own_fabric_nearer_than_recorded: 11`. Every one of those figures is true of the building. None of them is about the facade the item names.

## What matches

* **The camera is where the photographer stood** — **2.6 m** from the recorded viewpoint, on the photograph's own EXIF GPS, with the bearing agreeing to **0.7°**. Nothing in the framing is at fault.
* **The mass and the height are right.** 30.22 m of built fabric on **43 of 43** probe rays, against a real cornice line at about that height, and a plan bounding box that matches a grid-rotated real footprint.
* **The instant is the photograph's own** — EXIF `DateTimeOriginal`, a 52.5° Sun almost due south, and the facade in its own shade in both frames.
* **Central Park's own furniture is in the frame** — `lm_b_central_park_walls_gates.2` at 19.5 m is the park's perimeter wall, which is the nearest built thing on the east sidewalk and is exactly what stands there.
* **The park drives are car-free.** **14 vehicles were dropped** because the road graph put them on Central Park's East, West, Terrace or Center Drive, which have carried no private traffic since 2018 (J95). This is the rule doing its job on the one sheet in the batch where it applies.
* **The crowd is a museum crowd** — 255 people with **2 at LOD0**, the only sheet in this batch to draw any body at full detail, and they stand on the plaza rather than in the road.
* **The fleet is a Fifth Avenue fleet** — 29 sedans, **18 yellow taxis**, 11 SUVs, 6 boro taxis, 5 black cars and **3 MTA buses** on a Monday in September.
* **The park ground is exact where it can be checked** — within 150 m, **321 samples**, an under-fraction of **0.0**, a median clearance of **0.2 m** and a worst reading of **+0.015 m**; **2,328 faces** were cut out of it for the landmark's own ground.
* **The contrast matches** — standard deviation **0.2155** against **0.2045**, a ratio of **1.054**, and the means agree to the same figure.

## What does not match

* **The Fifth Avenue facade is not in the frame.** The colonnade, the three arches, the attic balustrade and the grand stair are all built and all on the far side of the model.
* **No banners.** The photograph carries three: two exhibition banners and the museum's own red one. This build invents no printed copy anywhere, and the named `SIGN_FACE_*` slots that would carry it are a runtime binding (B5, B15a).
* **No sky.** The building mass fills the top of the frame to the edge, so the photograph's blue sky and cumulus have no counterpart to compare against.
* **The render is brighter at the midtone than the photograph and far greyer** — p50 **0.4991** against **0.5535**, a ratio of **0.902**, mean **1.054×**, and chroma **0.0394** against **0.1002**, a ratio of **0.393**. A plain limestone box in shade carries almost no colour; the photograph's frame holds warm stone, three coloured banners, green trees and blue sky. The photograph's median sits **0.569 stops** above the grey convention and the render's **0.244**, a **−0.325-stop** difference (J83).
* **Props were capped to one in four** — **758 placed of 2,813 in range** at a **1,146,399-triangle** budget, **1,953 dropped for budget**, **1,940** of them tree rows, and **12** dropped on a suppressed building. Only 9 benches and 8 waste baskets survive on the frontage of the busiest museum in the country.
* **Kit was capped to under half** — **4,096 of 9,486 in range** at a **1,046,861-triangle** budget, of which **3,413 are windows**; **348** pieces were suppressed under landmark shells.
* **Trees: 148 drawn from modelled branches and 299 as impostor cards**, at a mean scale of **0.925**, with **103** species substituted and **13** impostor cards dropped — against the eastern edge of Central Park, which is a wall of mature trees.
* **Both tiles in range have no structures file** — 2 tiles, **2 without a file**, and the **2,364 triangles** of structures reported come from elsewhere in the radius. The Lexington Avenue line runs under this frame.
* **Six props across five kinds in range have no asset** — 2 artworks, 1 drinking fountain, 1 parks comfort station, 1 payphone, 1 real-time information sign.
* **Five park surface kinds keep the builder's flat colour** — infield clay, hard sport court, park grass, recreation grass and bare ground, because the texture catalogue holds walls, roofs, roadway and floors and no photographic set for any of them (J40).
* **The park ground sinks in the middle distance** — between 150 and 400 m the under-fraction is **0.1022** over 646 samples with a worst of **−1.901 m**, and beyond 400 m **0.0544** over 662 samples with a worst of **−4.266 m**. The redrape moved **410,951** vertices, up to **1.155 m** up and **1.169 m** down.
* **2,649 agents were dropped** — 1,097 pedestrians outside the radius, 732 at the agent triangle budget, 360 vehicles outside the radius, 212 pedestrians in the carriageway without crossing, 151 vehicles at the budget, 37 not on a walkable surface, 21 riderless bodies, 14 on a car-free park drive, **12 pedestrians above the observer**, 12 vehicles off the carriageway, 1 vehicle above the observer.
* **The frustum reports the museum 5.4° off axis at 116.9 m** while the subject's coordinate is 98.8 m away — the catalogue centroid of a 295 m by 339 m footprint against the piece being looked at.

## Measured for this assessment

| figure | source |
|---|---|
| colonnade 69,436 triangles, model-local x −144.8 to −8.7, y 9 to 29.7 m | glTF accessor bounds and index counts per node in `blender_out/landmarks/c_metropolitan_museum.glb` |
| pavilion front with the grand stair 12,941 triangles, local x −148.5 to −116.4, y 0 to 42 m | the same file; the stair is built into that node by `c_metropolitan_museum.py` |
| rear mass 280 triangles, 262.5 by 322.8 m, y 9 to 26.8 m | the same file; its bounding box equals the record's own `plan_extent` for `lm_c_metropolitan_museum.6` |
| base core 368 triangles, y 0 to 9 m | the same file |
| 82,377 of 84,671 triangles | the colonnade and pavilion front summed, against the model's total excluding its 1,128-triangle LOD1 node |
| the camera 103 m east of the model origin | the camera's NYC_TM x of −1031 against the catalogue `origin_tm` x of −1134.0 in `data/processed/landmarks/landmarks.json` |
| the footprint's bounding box, 295 m by 339 m | the catalogue's `bounds_local_m` for `c_metropolitan_museum`: x from −148.547 to 146.382 and y from −173.007 to 166.124, which is a real footprint whose walls run with the Manhattan grid measured in a north-aligned projection |
| local +x is east | that file's `placement` field: translate to `origin_tm`, apply no rotation, the model axes are already parallel to NYC_TM |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the Fifth Avenue facade is not in the frame | the builder's premise, written in its docstring, has Fifth Avenue west and Central Park east; both elevation tests follow it, so the 69,436-triangle colonnade and the 12,941-triangle pavilion front with the grand stair face the park and the 280-triangle rear mass faces the avenue | **geometry — open (J99), a single inverted premise in one builder** |
| the probe measured a 280-triangle back wall | the height probe measures the object standing at the subject's coordinate, and for a landmark built of parts that is whichever member is there (J74, J94); here it is the rear mass, and the lens and pitch were set from it | verification — declared, and correct about what it measured |
| the visible fraction reads 0.846 | 11 of 13 rays land on the museum's own fabric at 45.9 m; the figure is true of the building and says nothing about the facade the item names | verification — true and beside the point |
| no banners | no printed copy is invented anywhere; the face slots exist and the runtime text binding does not (B5, B15a) | declared decision |
| chroma 0.393 | a plain limestone mass in shade against a photograph holding banners, trees and sky — a consequence of the gap above, not a material fault | geometry |
| p50 0.902 | the photograph is developed 0.569 stops above the grey convention and the render 0.244 above (J83) | reference |
| 758 props of 2,813, 1,940 tree rows dropped | the props triangle budget at 1,146,399 | performance |
| 4,096 kit pieces of 9,486 | the kit triangle budget at 1,046,861 | performance |
| 348 kit pieces suppressed | the landmark shell replaces the tile's buildings and takes their kit with it | declared decision |
| both tiles without a structures file | those tiles are unbuilt, over the Lexington Avenue line | data — open |
| 6 props across five kinds unmapped | no asset exists for those kinds | data |
| five park surface kinds flat | the texture catalogue has no photographic set for clay, court, grass or bare ground (J40) | data — declared, named on the sheet |
| under-fraction 0.1022 mid-range, 0.0544 far | the park builder drapes on its own heightmap and the scene's differs; the redrape closes the near field to 0.0 and leaves a −4.266 m tail (J71) | geometry — open, bounded |
| 255 people of 2,042 asked | the agent triangle budget plus the placement rules, each with its own count | performance + verification |
| the frustum 5.4° off axis at 116.9 m | the catalogue centroid of a 295 m by 339 m footprint, not the piece being looked at | verification — cosmetic |
