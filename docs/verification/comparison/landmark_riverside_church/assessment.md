# Riverside Church

`landmark_riverside_church` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Riverside Church Mar 2026 27.jpg by Epicgenius, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2026-03-14 14:38:35, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Riverside_Church_Mar_2026_27.jpg) — the photograph's own view direction is derived from the image at **high** confidence. It is the nave's west elevation at close range: pointed arches with moulded reveals, bar tracery, a rose window, an octagonal stair turret, buttresses with set-offs, blue-black stained glass, warm Indiana limestone, and bare March trees along the kerb.

**Camera** — 40.81216, -73.963432 (NYC_TM -1133, 12455) at z 40.3 m NAVD88 | azimuth 127.1°, pitch +0.9° | 18 mm on 36 mm (90.0° horizontal, 74° vertical, landscape) | 1208x906. The camera stands on **this photograph's own EXIF GPS**, **113.7 m** from the item's recorded viewpoint; the item's recorded azimuth is 70.0°, **57.1° away**, and its viewpoint note names the **carillon tower** as what it looks at. The lens was widened to the **18 mm floor** and the record says the top of the subject is still cut off. The walk **did not move it**, on the tightest margin in the pass: the view azimuth is clear for **21.0 m** against a **20.0 m** requirement, the nearest built thing in the frame is `lm_c_riverside_church.7` **20.9 m** away, and the nearest simulated agent is a black car **6.1 m** from the lens (J98). The ground under it reads 38.722 m NAVD88, the 10th percentile of 113 samples within 12 m, range 38.51 to 39.37 m.

**Sun** — azimuth 212.2°, elevation 41.9° at 2026-03-14T14:38:35−04:00, from the photograph's own **EXIF DateTimeOriginal**; 851.9 W/m² direct normal, sky at strength 0.0331, Filmic, **+3.47 stops** metered and unclamped against a linear median of **0.016275** and a target of **0.18**. The physical rule would have given **0.05 stops** — so the meter lifted this frame by three and a half stops that the physics did not ask for, because a north-west-facing wall at 14:38 in March stands in its own shade.

**In the scene** — 4,500,265 triangles: 6 building tiles (287,184 tris, 0 missing, 0 LOD-substituted), 2 landmark models of which 1 can fall inside the 90.0° frame, 17,303 pavement polygons, 1,563 props, 4,335 kit pieces, 22 park-ground meshes over 414 surfaces, 21,568 triangles of structures, 51 vehicles and 364 people.

## Verdict — a visible fraction of exactly 1.000, and what all thirteen rays land on is a blank wall

**The sightline is perfect and it is the sheet's own indictment.** Thirteen rays cast, **13 clear**, **13 on the subject**, **0 into nothing**: `subject_visible_fraction` **1.0** and `subject_clear_fraction` **1.0**, the first exact 1.000 in this batch earned from a real landmark model rather than from a joined tile mesh. And the frame those rays measure is a **featureless grey plane** filling the upper two thirds, broken by one thin vertical slot, with a bare tree in front of it, two cars, a single pedestrian and a wide pale pavement across the bottom. Against it the photograph carries arcaded windows with deep moulded reveals, bar tracery, a rose window, a stair turret and buttresses. The verification has confirmed, to thirteen rays out of thirteen, that the camera can see all of something that is not there.

**The number that measures it is the colour.** Chroma **0.0242** against the photograph's **0.2347** — a ratio of **0.103**, the lowest on any sheet written so far by a wide margin. Warm limestone, blue-black glass and a March sky against neutral grey.

**Two mechanisms produce the blank wall, and both are recorded.** The landmark shell replaces the tile's own buildings, and with them **851 kit pieces were suppressed** — the windows, string courses, cornices and reveals the facade kit would have placed on a shell here. The landmark model that stands in their place carries the massing and no ornament: no tracery, no arch order, no buttress set-offs. So the sheet shows neither the kit's approximation of a facade nor the model's own, and the second half of J51 is the rest of the story — the openings are drawn, not cut, so even where a window is placed the reveal has no depth.

**The probe measured a nave, and the item is about a tower.** The viewpoint note names the carillon tower; the catalogue entry `c_riverside_church` is **120.1 m** tall and its origin stands **7.1 m** from the coordinate; and the object standing at that coordinate is `lm_c_riverside_church.1`, **30.91 m** above a ground of 35.97 m, **62.0 m by 59.8 m** in plan. So the lens was widened to 18 mm to contain a 31 m mass 40 m away, and the 120 m tower the sheet is nominally about was never the thing framed (J74, J94).

## What matches

* **The sightline and the framing are internally exact** — 13 of 13 rays, a clear fraction of 1.0, and the frustum putting the subject **18.8° off axis** at 41.3 m in a 90° frame.
* **The massing and the ground are right.** 30.91 m of built fabric on **43 of 43** probe rays, over a ground of 35.97 m on the Morningside ridge, which is why the camera stands at 40.3 m NAVD88.
* **The trees are bare, from the photograph's own date** — 14 March, inside `leaf_off`'s window, and the reference's kerbside trees are leafless (J97's working half). **86** are drawn from modelled branches within 120 m against 937 impostor cards.
* **The crowd clock reads Saturday** for 2026-03-14, which was a Saturday, and the fleet is a Saturday fleet: 30 sedans, 13 SUVs, 3 yellow taxis, 2 boro taxis, one box truck, one van, no buses.
* **Bodies at full detail** — 1 vehicle and 1 pedestrian at LOD0, 18 pedestrians at LOD1.
* **Nothing was capped in the props** — **1,563 placed of 1,677 in range**, **0 dropped for budget**.
* **The park ground is nearly exact near the camera** — within 150 m, **598 samples**, an under-fraction of **0.0151**, a median clearance of **0.167 m**. **314 faces** were cut for the landmark's own ground.
* **17,303 pavement polygons and none dropped**, including 4,277 sidewalk and 296 crosswalk.

## What does not match

* **The Gothic facade is a blank wall.** No tracery, no arch order, no rose window, no turret, no buttress set-offs.
* **A tenth of the photograph's colour** — chroma **0.103**.
* **851 kit pieces were suppressed** under the landmark shell, so the tile's own facade approximation is gone too.
* **The openings are drawn on the shell, not cut** (Stage 34 / J51, measured at +48 GB), so nothing in the frame has a reveal.
* **The probe measured a 31 m mass and the item is about a 120 m tower** (J74, J94).
* **The render is brighter and slightly harder than the photograph** — mean **0.5966** against **0.4588** (**1.3×**), p50 **1.124×**, sd **1.076×**, and a 5th percentile of **0.3076** against **0.1398**: the frame has no deep shadow in it because a flat wall has nothing to cast one. The photograph's median sits **0.112 stops below** the grey convention and the render's **0.25 above**, a **+0.362-stop** difference (J83).
* **The meter lifted the frame 3.47 stops where the physical rule wanted 0.05** — a north-west wall in March afternoon shade, developed up to a photographable level.
* **All three tiles in range have no structures file** — 3 tiles, **3 without a file** — although 21,568 triangles of structures came from elsewhere in the radius.
* **No park ground was built for two tiles in range** — `t_-1_13` and `t_-2_13` — so there is bare terrain there (J102).
* **11 props across six kinds in range have no asset** — 3 artworks, 2 drinking fountains, 2 memorials, 2 parks comfort stations, 1 misc structure, 1 parks building.
* **A simulated black car stands 6.1 m from the lens**, nearer than the nearest built thing at 20.9 m, and neither the walk nor the sightline counts it (J98).
* **1,343 agents were dropped** — 464 pedestrians outside the radius, 305 at the agent triangle budget, **205 in the carriageway without crossing**, 144 vehicles outside the radius, **94 off a walkable surface** (J101), 92 vehicles at the budget, 33 riderless bodies.
* **Beyond 400 m the park ground reads under the terrain on 0.2234 of 779 samples**, worst **−5.382 m**; the redrape moved **422,828** vertices, up to 2.266 m up and 1.411 m down.
* **No cloud.** The reference's sky is a clear March blue with thin cirrus; nothing in this build reads a historical sky.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the Gothic facade is a blank wall | the landmark shell replaces the tile's buildings and suppresses their 851 kit pieces, and the shell itself carries massing without ornament: tracery, arch orders and buttress set-offs are not classes this build models | **geometry — open, and the largest fidelity gap on this sheet** |
| a visible fraction of 1.000 on that wall | the sightline measures whether the subject's fabric is reachable, not whether it resembles the subject; on a blank mass both answers are yes (J78) | verification — true and useless here |
| chroma 0.103 | warm limestone, stained glass and a March sky against neutral grey — a consequence of the line above | geometry |
| no window reveals | the openings are drawn on the shell rather than cut (Stage 34 / J51, measured at +48 GB) | declared decision — physically impossible here |
| the probe measured 30.91 m for a 120.1 m subject | the probe measures the object at the coordinate and that object is a nave, while the item's own note names the carillon tower (J74, J94) | verification — declared, and correct about what it measured |
| +3.47 stops against a physical 0.05 | a north-west-facing wall at 14:38 in March stands in its own shade, and the development is metered on the frame (J83) | verification — declared, and correct |
| mean 1.3, p05 0.3076 | a flat wall casts no shadow, so the frame holds no dark values; the photograph is developed 0.112 stops below the grey convention and the render 0.25 above (J83) | geometry + reference |
| all three tiles without a structures file | those tiles are unbuilt, under a block served by the Broadway line | data — open |
| no park ground for two tiles | 85 % of the city's mapped open space was never draped (J102) | data — open (J102) |
| 11 props across six kinds unmapped | no asset exists for those kinds | data |
| a car 6.1 m from the lens | the walk and the sightline count built fabric only, by J49's declared decision, and nothing acts on the agent distance the record publishes (J98) | verification — open (J98) |
| 364 people of 813 asked, 94 off a walkable surface | the agent triangle budget plus the crowd's walkable test (J101) | performance + verification |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
