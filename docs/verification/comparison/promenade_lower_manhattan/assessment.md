# Brooklyn Heights Promenade looking at Lower Manhattan

`promenade_lower_manhattan` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Brooklyn Heights Promenade January 2023 006.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2023-01-20 14:33:49, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Brooklyn_Heights_Promenade_January_2023_006.jpg) — the view direction is derived from the image at **high** confidence. It is the Promenade's own view: the whole Lower Manhattan ridge across the East River, Pier 5 and Brooklyn Bridge Park below with its bare January trees, and a sky of broken winter cloud that is half the picture.

**Camera** — 40.696158, -73.997781 (NYC_TM -4038, -426) at z 21.7 m NAVD88 | azimuth 324.4°, pitch 0.0° | 28 mm on 36 mm (65.5° horizontal) | 1208x906. The camera stands on **this photograph's own EXIF GPS**, **29.5 m** from the item's recorded viewpoint, and the heading agrees with the item's recorded 324.3° to **0.1°**. It was **not moved**, and the record explains why in terms specific to this kind of item: *"the eye point stands on `t_-5_-1_park_park_ground_grass`, but this camera's position is the photograph's own EXIF GPS rather than a nominal viewpoint standing for a whole deck, so there is nothing to walk to"*. The view azimuth is clear for **150.0 m** and no simulated agent stands within 60 m. The lens is chosen for the view rather than by default: *"promenade skyline: the reference photographs carry the whole Lower Manhattan ridge plus the East River foreground, about 65 deg horizontal"*. The ground under the lens reads 20.144 m NAVD88 from 16 samples within 5.0 m, range 19.9 to 20.17 m.

**Sun** — azimuth 216.8°, elevation **20.4°** at 2023-01-20T14:33:49−05:00, from the photograph's own **EXIF DateTimeOriginal**; 658.5 W/m² direct normal, sky at strength 0.0403, Filmic, **+0.94 stops**. Metered: the linear median is **0.093991**, over half the 0.18 target, so the development is only **0.937 stops** — and for once the physical rule is **higher**, at **1.09**.

**In the scene** — 4,500,023 triangles: **90 building tiles (1,652,322 tris), 11 missing, 20 substituted by a lower LOD**, 32 landmark models of which 15 fall inside the 65.5° cone, 25,660 pavement polygons, **231 props**, **113 kit pieces**, 28 park-ground meshes, **48 tiles of structures (400,836 tris) with 33 having no file**, 45 vehicles and 225 people. The water table names **32 separate bodies**, from the Hudson and the East River down to Prospect Lake and the Ambergill Pond, with 37,567 quads on the flattened water surface.

## Verdict — the visible fraction is 0.0 for the tallest building in the hemisphere, and the whole chain from cause to effect is inside this one record

**Three recorded faults compound here, in order.** First, the height probe cast 43 rays, 41 landed on fabric, and it measured **292.65 m** on `lm_b_one_world_trade_center.6`, an object 75.0 m square. The catalogue entry 35.0 m away carries **541.3 m**, which is One World Trade Center's spire tip. So the ray met one of the tower's tapering facets and stopped there, **248.65 m** short, and J74's rule preferred that measurement to the entry. That is J94's fault on the tallest building in the western hemisphere.

**Second, the fan was then centred on the mid-height of the wrong figure.** `subject_aimed_at` is *"the subject's mid-height, 146.3 m above its ground"* and `subject_fan_v_half_angle_deg` is **3.69°**. From a lens 21.7 m up, 2,265 m away, that aim point sits a little over three degrees above the horizon, and the fan's own outermost ray reaches only a few degrees higher. One World Trade Center's roof stands about ten degrees above this lens. **The fan is aimed below the skyline, at the part of downtown that other buildings stand in front of.** Had the probe returned the catalogue's 541.3 m, or even the tower's roof, the aim would have been two and a half times higher and the rays would have cleared the intervening ridge. This is J106's fault seen from the other end: J106 records a fan aimed too high on a tall subject seen from close, and this is the mirror case — aimed too low on a tall subject seen from far, for the same reason, because the centre is the mid-height of the measurement rather than the midpoint of the subject's true angular extent.

**Third, what stopped every ray is a joined tile mesh.** All 13 rays are blocked, `subject_clear_fraction` is **0.0**, and every one of them stops at **1,163.0 m** on `t_-5_0_limestone` — one object holding every limestone surface in a Lower Manhattan tile (J94 again). The published `subject_visible_fraction` is **0.0**, and `frame.usable` is nonetheless `true`, which is J100: the frame gate is a luminance test and nothing else.

**And yet the picture is good.** This is the most expensive scene in the pass to build — **90 building tiles at 1,652,322 triangles**, 279,702 triangles of terrain at 2.5 m spacing, 48 tiles of structures at 400,836 triangles — and the result is a Lower Manhattan ridge that reads as Lower Manhattan: One World Trade Center's tapering slab and spire at the centre, the setback towers of the Financial District stepping down to the water, the Battery's low edge at the left. A reader comparing the two halves would recognise the city. **The sheet's own headline number says it contains none of its subject, and that number is wrong about the picture** — which is exactly why J100 asks for the zero to be declared rather than published as a bare measurement.

**What the render does not have is the sky and the ground.** The photograph's upper half is broken winter cloud with light moving across the skyline; the render has an unbroken Nishita dome at strength 0.0403. Its lower third is an unrelieved pale green plate — the park-ground grass surface, which the record says is *"kept the builder's colour — analytic: the texture catalogue has no photographic set for mown grass"* (J40). Between them they account for the two worst measured ratios on the sheet: contrast at **0.486** of the photograph's and brightness at **0.809**.

## What matches

* **The skyline is recognisable.** 90 building tiles at 1,652,322 triangles and 32 landmark models, with One World Trade Center's tapering slab and spire in the right place and the Financial District's towers stepping down to the Battery.
* **The camera and the heading are both the photograph's own.** The EXIF GPS, and a bearing that agrees with the item's recorded azimuth to **0.1°** — the closest agreement in any camera block read this round.
* **The lens was chosen for the view, not by default**, at 28 mm and 65.5° horizontal, because a promenade sheet has to carry the whole ridge plus the river foreground.
* **The walk correctly declined to move.** The record distinguishes a photograph's own GPS from a nominal viewpoint standing for a whole deck, and says there is nothing to walk to — the right answer, stated in the right terms.
* **The height probe found fabric on 41 of 43 rays** and the object it measured is a real 75.0 m square piece of the tower, not a tile mesh.
* **The scene arrived bright and needed almost nothing.** 0.937 stops on a linear median of 0.093991, and the physical rule would have asked for *more* — the only sheet read this round where the measurement is below the rule.
* **Structures are here in force**: 48 tiles imported for **400,836 triangles**, the largest structures contribution of any sheet read this round, which is what a Brooklyn waterfront and a Manhattan shoreline need.
* **The water is comprehensive**: 32 named bodies and 37,567 quads on the flattened surface.
* **The park ground is correct where the camera can see it**: 296 samples within 150 m, `under_frac` **0.0068**, median clearance +0.211 m.
* **The date is right and the trees are bare.** 20 January is inside the leaf-off window, and the promenade's trees in the render are bare-canopy, as they are in the photograph (J97).
* **Only 68 pedestrians were lost to the agent triangle budget** — the smallest such loss read this round.

## What does not match

* **The published visible fraction is 0.0** for a subject that is plainly in the picture, and `frame.usable` is true beside it (J100).
* **The height is 292.65 m for a 541.3 m tower** — a 248.65 m under-measurement, because the ray met a facet of the taper (J94).
* **The fan is aimed below the skyline.** Centred a little over three degrees above the horizon on a subject whose roof is about ten degrees up, so every ray runs into the Financial District instead of over it (J106).
* **All thirteen rays stop on one joined limestone tile mesh** 1,163 m away (J94).
* **No cloud, and the sky is half the reference.** The render's contrast is **0.486** of the photograph's, the flattest ratio on any sheet read this round, and its 95th percentile is 0.6166 against the photograph's 0.906.
* **The foreground is a flat green plate.** Brooklyn Bridge Park's ground is drawn as the park-ground builder's own colour because the texture catalogue has no photographic set for mown grass (J40), and here it occupies a third of the frame.
* **Eleven building tiles were not built at all**, and **twenty more were drawn at a lower LOD than their distance asks** — on the one sheet in the pass whose subject is a skyline two kilometres away.
* **Thirty-three of the forty-eight structures tiles have no file.**
* **Ninety-seven per cent of the props in range were dropped.** 231 drawn of **8,716** at a **316,792**-triangle budget, **8,464 dropped**, including **8,435 tree rows**, with 14 impostor cards dropped as opaque. The promenade's own planting and the pier's trees are almost entirely absent.
* **The kit is effectively absent.** 113 pieces drawn of 1,238 in range against a **31,850**-triangle budget — the smallest kit budget in the pass by an order of magnitude — of which 88 are windows and 3 cornices. The scene spent its triangles on the skyline and had nothing left for the block the camera stands on.
* **Almost a stop of the brightness difference is exposure.** The photograph sits **1.085 stops above** the grey convention — a bright overcast winter frame — and the render 0.236 above it, a **−0.849-stop** gap, so mean reads 0.809× and p50 0.764× (J83).
* **The render carries slightly more colour than the photograph**, chroma 1.144×, which on this sheet is the flat green plate rather than a match.
* **The park ground sinks badly beyond 400 m**: 0.3872 of 3,179 samples, worst case **−7.373 m**, and 0.3423 across all 3,745 samples.
* **209 pedestrians were dropped for not being on a walkable surface** — the Promenade itself is not a road-network sidewalk class (J101) — so the railing the photograph's own viewpoint stands at is empty. 225 people are drawn where the density table asked for 1,244; 291 vehicles and 1,825 people were simulated and **1,846 dropped**: 1,051 pedestrians outside the radius, 272 in the carriageway without crossing, 238 vehicles outside the radius, 209 not on a walkable surface, 68 at the agent budget, 6 riderless bodies and 2 off the carriageway.
* **Every agent is at the coarsest LOD**: all 45 vehicles and all 225 people at LOD2.
* **Four green boro taxis against a single yellow cab** in Brooklyn Heights — the green share is right for the borough, and one yellow cab in a frame that also holds Lower Manhattan is not (J105).
* **The river is a mirror.** Open water is a flat specular plane with no wave state and no turbidity (J103), so the East River reflects the skyline cleanly where the photograph's is choppy and grey.

## Measured for this assessment

| figure | where it comes from |
|---|---|
| the aim point sits a little over three degrees above the lens and the tower's roof about ten | the recorded subject ground of 3.36 m, the recorded aim at 146.3 m above it, the recorded camera height of 21.7 m and the recorded distance of 2,265.1 m; One World Trade Center's roof is the difference between the catalogue's 541.3 m spire tip and its published 417 m roof |
| 248.65 m of under-measurement | the recorded probe height of 292.65 m against the recorded catalogue height of 541.3 m |
| the smallest kit budget in the pass, the largest structures contribution and the flattest contrast ratio read this round | this sheet's 31,850-triangle kit budget, its 400,836 triangles of structures and its 0.486 sd ratio, against every other record in the pass for the first and the thirty-nine sheets read in the preceding rounds for the others |
| the only sheet read this round whose metered development is below the physical rule | this sheet's 0.937 stops against its `physical_rule_stops` of 1.09 |
| 20 January is inside the leaf-off window | the `leaf_off` rule in `blender/verify/render_sheets.py`, true for a date on or after 15 November or on or before 15 April (J97) |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the published fraction is 0.0 on a subject that is in the picture | three recorded faults in series: the probe measured a facet of the taper rather than the tower (J94), the fan was centred on the mid-height of that measurement rather than on the subject's true angular extent (J106), and every ray then stopped on a joined limestone tile mesh (J94). The frame gate is a luminance test, so the zero is published beside `usable: true` (J100) | **verification — open; this sheet is the clearest single demonstration of all four entries at once** |
| the height is 292.65 m for a 541.3 m tower | the ray at the item's coordinate met one of the tower's 75.0 m square tapering facets; nothing in the probe prefers the tallest member whose footprint contains the coordinate (J94) | **verification — open** |
| no cloud, contrast 0.486 | nothing in this build reads a historical sky, and here the sky is half the reference | **reference — no source exists** |
| the foreground is a flat green plate | the texture catalogue has no photographic set for mown grass, so the park-ground builder's own colour is kept (J40) | **data — declared, no source** |
| 11 building tiles not built and 20 drawn at a lower LOD | those tiles have no shell file, and the LOD substitution is the streaming rule working as designed on a two-kilometre view | data + performance |
| 33 of 48 structures tiles have no file | those tiles were not built (B13 remainder) | **data — open** |
| 8,464 props dropped, 8,435 of them trees | the props triangle budget at 316,792 triangles, after 90 building tiles took 1,652,322 | **performance — the scene cost is the skyline** |
| the kit withheld — 113 drawn of 1,238 in range | the kit triangle budget at 31,850 triangles, for the same reason | **performance** |
| 0.849 stops of exposure difference | the photograph was developed 1.085 stops above the grey convention and the render is metered to 0.236 above it (J83) | reference — declared, and correct |
| the park ground 0.3423 under the terrain, worst case -7.373 m | the park surfaces were draped on the fine grid and this scene's terrain coarsens to 40.0 m over a five-kilometre radius (J40, J96) | verification — declared |
| the Promenade's railing is empty | the crowd's walkable test reads only road-network sidewalk classes, so a promenade is not standable and 209 bodies were dropped for it (J101) | **verification — open** |
| the river is a clean mirror | open water is a flat specular plane with no wave state or turbidity (J103) | declared decision |
| one yellow cab in a frame containing Lower Manhattan | the runtime splits the taxi share 70/30 yellow to green everywhere with no geography, and this camera's own cell is in Brooklyn (J105) | data — open |
