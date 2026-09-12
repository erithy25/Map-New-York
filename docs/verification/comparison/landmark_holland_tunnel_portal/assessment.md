# Holland Tunnel Manhattan portal

`landmark_holland_tunnel_portal` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Holland Tunnel Entrance - panoramio.jpg by Idawriter, CC BY-SA 3.0 (https://creativecommons.org/licenses/by-sa/3.0), taken 2010, 1920x1369. [Commons page](https://commons.wikimedia.org/wiki/File:Holland_Tunnel_Entrance_-_panoramio.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.72427, -74.00680 (NYC_TM -4838, 2676) at z 4.9 m NAVD88 | azimuth 327.2°, pitch +4.5° | 35 mm on 36 mm (54.4° horizontal) | 1236x882. Position and heading both come from the photograph: its own EXIF camera GPS, **81.3 m** from the item's recorded viewpoint, and 327.2° is the bearing from there to the subject; the item's recorded azimuth of 309.1° is 18.1° away. The recorded viewpoint was **boxed in** — the azimuth closed **53 m** ahead against the 80.0 m needed — so the camera was **moved 44.6 m** onto the nearest surveyed sidewalk, ranked on how much of the subject it sees. The record then states the walk's own limit: *No point within 80 m had 80 m of open air along the view azimuth with nothing built inside 8 m of the lens*, so the frame is closed off **96 m** ahead. Nothing built stands within 20 m of the lens and no agent either. Ground under the camera reads **3.325 m** NAVD88, the 10th percentile of **113** heightmap samples within 12 m, range 3.22 to 3.94 m.

**Sun** — azimuth 284.1°, elevation 20.2° at 2010-06-21T18:30:00−04:00. **The instant is chosen, not measured** (J80): the photograph carries only a year, so 21 June is assumed and **18:30 is chosen** because *of the hours that put the Sun above 20 deg it is the one whose bearing (284 deg) comes closest to the view azimuth (309 deg), 25 deg off, so the Sun is behind the camera and lights what it looks at*. 655.2 W/m² direct normal, sky at strength 0.0404, Filmic, **+5.68 stops**, declared: *under-lit: the scene needed +5.68 stops to read as a picture, more than the 4 a photographer recovers hand-held*. The linear frame's median is **0.003512** against a target of 0.18; the physical rule would have given **+1.11 stops** (J83).

**In the scene** — 4,500,613 triangles: 7 building tiles (314,634 tris, none missing, none LOD-substituted), **1 landmark model and 0 of it inside the 54.4° frame**, 33,549 pavement polygons with **0 dropped**, 802 props, 5,458 kit pieces, 35 park-ground meshes over 359 surfaces, 3 structures tiles (69,216 tris) with **4 without a file**, 50 vehicles and 422 people, terrain 91,592 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the portal, its gantry and its sign are all absent behind a street tree forty-two metres out, and the "subject height" the frame was built from is a glass curtain wall measured off a tile mesh a kilometre across

**Visible fraction 0.000.** Thirteen rays, **0 clear, 0 on the subject**, every one stopped at **41.9 m** by `prop_tree_honeylocust_large_79`. The reference is the entrance plaza: the steel gantry across the roadway carrying an illuminated HOLLAND TUNNEL sign and a STAY IN LANE indicator, the brick loft buildings behind it, a police booth, and a queue of cars. None of that is in the render, which shows a tree-lined street, a pale plaza, a row of window-gridded buildings and pedestrians.

**The subject height is measured off the wrong kind of object.** The probe reports **34.67 m** above a ground of 3.54 m — but its object is `t_-5_2_glass_curtain`, a **tile mesh** whose extent is **1,013.3 m by 1,001.7 m**: every glass-curtain surface in that tile joined into one. The record says a tile mesh's extent is not the subject's and does not use it (J74), and the height it reports is still a curtain wall somewhere in Hudson Square rather than the tunnel portal. 25 of 43 rays found fabric. This is J94's tile-mesh case, as on Rockefeller Center and Castle Williams.

**The instant is the strongest thing on this sheet.** The photograph carries a year and nothing else, and rather than falling back to a fixed hour the chain **chose** 18:30 on 21 June because that is the hour whose sun bearing comes closest to the view azimuth — 25° off, so the sun is behind the camera and lights what the frame looks at. That is J80's repair working exactly as specified, and the record explains it in a sentence a reader can check.

**The trees are the best thing in the picture and part of the problem.** **118 of 237** are drawn from modelled branches, with full crowns and real shadows — and one of them is what closes every ray to the subject. The clearance walk weighs built fabric and never weighs a tree (J88's family).

**The tonal pairing is close by coincidence.** Mean **1.023×**, median **1.107×**, chroma **1.032×**, with the two development offsets **0.316 stops** apart. A shaded street under full canopy at +5.68 stops and a 2010 compact-camera photograph of a tunnel mouth happen to land in the same place; nothing here is evidence about the build.

## What matches

* **The chosen instant is defensible and explained**: 18:30 on 21 June, picked because its sun bearing is closest to the view azimuth of the hours that clear 20° elevation (J80).
* **118 of 237 trees are drawn from modelled branches** with real crowns and shadows.
* **The development is metered and declared under-lit** with its number, +5.68 stops (J83).
* **The pavement is the largest complete set in this queue**: 33,549 polygons, **0 dropped**, including **18,391** white markings, 5,324 roadbed, 3,886 sidewalk, 3,728 curb and 1,031 crosswalk.
* **Structures carry 69,216 triangles** on the 3 tiles that have files — the Hudson Square viaducts and seawalls.
* **The clearance is clear where it can be**: nothing built within 20 m of the lens and no agent either.
* **The record names every limit**: the 53 m closure, the 44.6 m move, the walk's failure to find a compliant point, the tile-mesh subject and the 0.000 verdict.
* **Near-field ground is perfect**: within 150 m, **0.0** of 46 park-surface samples sit under the terrain.
* **The crowd is substantial**: 422 people drawn.

## What does not match

* **The portal, the gantry and the sign are absent from the frame**, with visible fraction **0.000** and every ray stopped by a street tree at 41.9 m.
* **No landmark model falls inside the frame** — 1 placed, **0 in the cone**.
* **The subject height comes from a tile mesh 1,013 m across** (J94).
* **The frame is 5.68 stops under-lit**, and the walk could not find a compliant point within 80 m.
* **Eighty-three per cent of the props are missing**: 802 placed of **4,603 in range**, with **3,527 dropped for the triangle budget** of 1,203,551 and 14 cards dropped — the largest proportional prop shortfall in this queue.
* **5,458 of 22,167 kit records were drawn**, capped at a 1,150,471-triangle budget.
* **2,589 tree rows did not fit** the props budget, and **0** of the 119 cards are procedural canopy stems.
* **Four of 7 structures tiles have no structures file.**
* **Beyond 400 m the park surface sits under the terrain on 0.2926 of 1,073 samples**, minimum **−2.865 m** (J85).
* **Thirty-nine props across five kinds were wanted in range and have no asset**: 28 misc structure, 5 artwork, 3 drinking fountain, 2 memorial, 1 billboard. On a tunnel plaza, "misc structure" is the toll canopy, the ventilation buildings and the police booth.
* **Nine park-ground surface kinds fall back to the builder's flat colour** (J40).
* **The crowd is a fourteenth of the ask**: the table wanted 1,135 vehicles and 5,817 people; 1,325 and 3,000 were simulated and **3,853** dropped — 788 pedestrians and 552 vehicles at the agent triangle budget, **662** pedestrians in the carriageway without crossing, 49 vehicles with no roadway under them, 25 pedestrians with no sidewalk, and **33 riderless bodies**.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| visible fraction 0.000, the portal behind a tree | a large honeylocust 41.9 m out closes all 13 rays; the clearance walk weighs built fabric and never weighs a tree (J88's family), and no point within 80 m met its rule | **verification — open** |
| no landmark in the frame | the frustum found 0 of 1 in the cone after the 44.6 m move changed the bearing | verification — open |
| the subject height comes from a tile mesh 1,013 m across | the probe takes the object standing at the coordinate, and in Hudson Square that object is every glass-curtain surface in the tile joined into one (J94) | **verification — open, J94** |
| +5.68 stops, under-lit | a shaded street under full canopy at 20° sun elevation; declared with its number (J83) | verification — declared |
| 802 props of 4,603 in range, 2,589 tree rows dropped | the props triangle budget at 1,203,551, which dropped 3,527 | **performance** |
| 5,458 kit pieces of 22,167 in range | the kit triangle budget at 1,150,471 | **performance** |
| 4 of 7 structures tiles without a file | no structures file was built for those tiles | **data — open, four tiles unbuilt** |
| 39 props unmapped, 28 of them misc structure | no asset exists for those kinds, and on a tunnel plaza that kind is the toll canopy and the ventilation buildings | **data — open** |
| 0.2926 of far park ground under the terrain | the terrain grid coarsens to 40 m beyond the near band (J85) | geometry — open, measured |
| nine park surface kinds flat-coloured | the texture catalogue has no photographic set for any of them (J40) | **declared decision** |
| 422 people where the table asked 5,817 | the agent triangle budget plus the placement rules, each with its count | performance + verification |
