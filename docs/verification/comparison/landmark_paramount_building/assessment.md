# Paramount Building (1501 Broadway)

`landmark_paramount_building` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Paramount Building Times Square.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2021-08-25 12:41:13, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Paramount_Building_Times_Square.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.75666, -73.98644 (NYC_TM -3077, 6292) at z 17.4 m NAVD88 | azimuth 4.1°, pitch +23.3° | 18 mm on 36 mm (90.0° horizontal) | 1208x906. Position and heading both come from the photograph: its own EXIF camera GPS, **188.6 m** from the item's recorded viewpoint, and 4.1° is the bearing from there to the subject. The item's recorded azimuth of 210.0° is **154.1° away** — the nominal viewpoint looks at this building from the other side — so using the photograph's own geometry is the only way the two frames can be the same view. The lens was **widened from 35 mm to the 18 mm floor** and the axis tilted **+23.3°**, and even then the top of the subject is cut off: `lm_c_times_square.49` stands 92 m above the lens at 63 m, **56° above the horizon**, against a 74° vertical frame. **The verticals converge, so this frame is not comparable with the photograph on proportion.** The camera was **not moved** — the viewpoint is in open air, the view azimuth clear for **47.5 m** against the **31.5 m** this frame needs, the nearest built thing `t_-4_6_glass_curtain` **19.7 m** away at 45°. Ground under the camera reads **15.76 m** NAVD88, the 10th percentile of **113** heightmap samples within 12 m, range 15.67 to 16.12 m.

**Sun** — azimuth 171.9°, elevation 59.5° at 2021-08-25T12:41:13−04:00, from the photograph's own **EXIF DateTimeOriginal**; 917.5 W/m² direct normal, sky at strength 0.0310, Filmic, **+2.78 stops and not clamped**. The linear frame's median is **0.026144** against a middle-grey target of 0.18, so the meter asked for **+2.78 stops** and got exactly that. The physical rule would have given **0.0 stops**, which is the whole case for metering (J83): a late-August noon at 59.5° elevation is the brightest condition in this pass and still needs nearly three stops to reach a photographable level.

**In the scene** — 4,500,156 triangles: 4 building tiles (247,682 tris, none missing, none LOD-substituted), 4 landmark models of which 2 fall inside the 90.0° frame, 26,372 pavement polygons with **0 dropped**, 1,385 props, 6,144 kit pieces, 13 park-ground meshes over 75 surfaces, **0 triangles of structures**, 53 vehicles and 249 people, terrain 86,520 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the best-behaved frame of this pass on light and sightline, and the subject's two defining features are both missing: the street-level ornament and the setback tower with its clock and globe

**Everything the verification chain measures, it measures cleanly here.** The development is **+2.78 stops unclamped** — one of the few daylight frames in the pass that the meter could satisfy. The sightline is the strongest so far: 13 rays, **13 clear**, **9 on the subject**, clear fraction **1.0**, visible fraction **0.692**. The height probe is **43 of 43** rays on built fabric, and the plan extent is measured off the object rather than guessed: **54.5 m by 54.2 m**. The camera stood where the photographer stood and was not moved.

**And the picture is a plausible brick tower on a Times Square street.** The tan brick, the deep window reveals, the setbacks stepping up the right-hand mass, the wet-looking asphalt, the taxis and the 249 people on the sidewalk all read as the block in question. Compared with the two sheets either side of it in this queue, this one is a render of the right thing from the right place.

**What it is not is a picture of the Paramount Building's face.** The photograph's lower half is the building's ornate cast-iron and limestone entrance surround with the 1501 clock in the middle of it. The render's lower third of that same wall is **a flat grey plinth**: no storefront, no marquee, no arch, no ornament. And the item's own subject line names the *setback clock tower and globe*, which the render's massing does not carry — the probe measures the object at the subject's coordinate topping out at **94.62 m** above a ground of 15.36 m, a flat-shouldered mass where the photograph implies a stepped crown above it.

**The subject is also not a building in this build; it is a member of a composite.** The probe's object is `lm_c_times_square.49` and the nearest catalogue origin is `c_times_square` — the Times Square composite, 113.8 m away, carrying **365.8 m**, which is not this building's height. The frustum then reports **Times Square at 197.1 m, 72.5° off axis** for a subject 63.0 m away and dead ahead: the cone test uses the composite's centroid, so on this sheet it names the wrong thing in the wrong direction.

## What matches

* **The development is metered and unclamped**, +2.78 stops from a median linear luminance of 0.026144 against the 0.18 target (J83). This is what a correctly exposed frame in this pass looks like.
* **The sightline is unobstructed**: 13 of 13 rays clear, 9 landing on the subject, 2 into nothing, 5 on the subject's own fabric nearer than the recorded coordinate — which is the signature of a wide building seen from close range, not of an occluder.
* **The height probe is complete and the extent is real**: 43 of 43 rays on built fabric, 94.62 m above the ground at the subject's coordinate, plan extent 54.5 m by 54.2 m taken from the bounding box of the object the height was measured off (J74).
* **The camera needed no intervention** — open air, no move, no deck rule, azimuth clear for 47.5 m against 31.5 m needed.
* **The brick and the reveals are the right material and the right depth.** Both halves show a warm brick pier-and-spandrel wall with windows set well back; the render's 5,642 window pieces are doing the work the photograph's shadow lines do.
* **The pavement is complete**: 26,372 polygons, **0 dropped**, including 10,455 white markings, 5,783 sidewalk, 4,387 roadbed, 3,307 curb, 1,635 plaza and 518 crosswalk.
* **Near-field ground is perfect on this sheet**: within 150 m, **0.0** of 99 park-surface samples sit under the terrain, median clearance **+0.12 m**, minimum +0.052 m, no z-fighting.
* **Trees are scaled from their own rows**: 126 placed, mean scale **0.926**, **0** out of band, **0** impostor cards dropped.
* **Agents are at mixed detail**: of 53 vehicles, 9 at LOD1; of 249 people, **49 at LOD1 and 3 at LOD0**.
* **The crowd is this hour's crowd**: seed 20260907, 120 s of simulated time, a weekday profile for a Wednesday, 2021-08-25.

## What does not match

* **The subject's street wall is a blank grey plinth.** The photograph's lower half — the ornamental surround, the marquee line and the 1501 clock — has no counterpart in the render, where the same wall meets the sidewalk as unbroken grey. 165 storefront pieces are in the scene and none of them is on this building's face.
* **The setback clock tower and globe, which the item names as its subject, are absent.** The massing tops out flat at 94.62 m above its ground.
* **The subject is a member of a composite, not a building.** `lm_c_times_square.49`, with the composite's catalogue origin 113.8 m away carrying 365.8 m — a figure that cannot be used for this subject, and correctly was not (J74).
* **The frustum names Times Square 72.5° off axis at 197.1 m** while the subject is 63.0 m away on the axis: the cone test uses the composite's centroid.
* **No structures at all**: **0 tiles imported, 4 without a file, 0 triangles** — beneath the Times Square subway interchange and the 42nd Street shuttle.
* **Not one tree is drawn from modelled branches.** All 126 in range are six-triangle impostor cards, **0** are procedural canopy stems, and **1,215 tree rows** did not fit the props budget of 1,186,595 triangles.
* **93,689 kit records were in range and 6,144 were drawn**, capped at a 1,118,824-triangle budget — one piece in fifteen.
* **The render is flatter and paler than the photograph**: standard deviation **0.1628** against **0.2175** (**0.749×**), median **0.497** against **0.6022** (**0.825×**), chroma **0.117** against **0.1698** (**0.689×**). The two exposure offsets from the grey convention are **+0.231** and **+0.835** stops, a **0.604-stop** difference, so part of that median gap is the photograph's own development and not the scene (J83).
* **No cloud and no sky gradient to match.** The reference's deep blue August sky is a single Nishita dome in the render at strength 0.0310; nothing in this build reads a historical sky.
* **Fifty-one props across eight kinds were wanted in range and have no asset**: 22 misc structure, 11 artwork, 6 memorial, 5 drinking fountain, 3 parks building, 2 passenger-information sign, 1 parks comfort station, 1 vending machine.
* **A simulated taxi stands 9.3 m from the lens** at 15° off axis — outside the 8 m of nothing-built the walk enforces against geometry, but only just, and the rule still does not apply to the crowd (J91).
* **Beyond 400 m the park surface sits under the terrain on 0.1967 of 1,098 samples**, minimum **−2.125 m**, after a redrape that moved 31,154 vertices by up to 1.626 m (J85).
* **The crowd is a twelfth of the ask.** The density table wanted **1,314 vehicles and 2,999 people**; 1,548 and 3,000 were simulated and **4,246** dropped — 1,403 pedestrians and 630 vehicles at the agent triangle budget, 980 pedestrians and 806 vehicles outside the radius, 243 pedestrians in the carriageway without crossing, 114 not on a walkable surface, 30 vehicles not on a carriageway, 11 pedestrians and 7 vehicles above the observer, and **22 riderless bodies**.
* **Four park-ground surface kinds fall back to the builder's flat colour** — sport court, park grass, recreation grass, bare ground — because the texture catalogue has no photographic set for any of them (J40).

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the subject's street wall is a blank grey plinth | the facade kit places storefronts from the building rows of the tile, and a landmark composite's own shell carries no storefront band of its own; 165 storefront pieces in the scene, none on this face | **geometry — open, landmark shells have no ground-floor treatment** |
| no setback clock tower or globe | the composite's massing for this building ends flat at 94.62 m; ornament and crown features are not a class this build models | geometry — declared scope |
| the subject is a composite member with a 365.8 m catalogue origin | Times Square is modelled as one composite landmark, so its members have no individual catalogue entries; the probe correctly measured the object instead of reading the entry (J74) | **data — declared, and handled** |
| Times Square reported 72.5° off axis at 197.1 m | the frustum test uses a composite's centroid, not the member being looked at | verification — open |
| no structures on any tile | 4 tiles in range and none has a structures file, over the Times Square interchange | **data — open, four tiles unbuilt** |
| 0 modelled trees, 1,215 tree rows dropped | the props triangle budget at 1,186,595 triangles; no mapped woodland polygon in this radius | performance + declared rule |
| 93,689 kit records in range, 6,144 drawn | the kit triangle budget at 1,118,824 | performance |
| sd 0.749×, p50 0.825×, chroma 0.689× | partly the photograph's own development, 0.604 stops from the render's, and partly a build with no per-building facade colour (J66 remainder) | reference + **data — open** |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
| 51 props across eight kinds unmapped | no asset exists for those kinds | data |
| a taxi 9.3 m from the lens | the 8 m nothing-built rule applies to geometry and not to the crowd (J91) | verification — open |
| 0.1967 of far park ground under the terrain | the terrain grid coarsens to 40 m beyond the near band (J85) | geometry — open, measured |
| 249 people where the table asked 2,999 | the agent triangle budget plus the placement rules, each with its count | performance + verification |
| four park surface kinds flat-coloured | the texture catalogue has no photographic set for any of them, and the builder's colour is kept rather than the nearest wrong material (J40) | **declared decision** |
