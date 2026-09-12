# 55 Hudson Yards

`landmark_55_hudson_yards` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:55 Hudson Yards 001.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-10-14 12:33:01, 1920x2560. [Commons page](https://commons.wikimedia.org/wiki/File:55_Hudson_Yards_001.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.75456, -74.00116 (NYC_TM -4320, 6060) at z 7.9 m NAVD88 | azimuth 331.7°, pitch +29.6° | 18 mm on 36 mm (73.7° horizontal, 90.0° vertical, portrait) | 904x1206. Position and heading both come from the photograph: its own EXIF camera GPS, **160.9 m** from the item's recorded viewpoint, and 331.7° is the bearing from there to the subject. The item's recorded azimuth of 280.0° is **51.7° away** and belongs to its nominal viewpoint. The lens was **widened from 35 mm to the 18 mm floor** and the axis tilted **+29.6°**, and the top of the subject is still cut off: `lm_c_hudson_yards.40` stands 238 m above the lens at 90 m, **69° above the horizon**. **The verticals converge, so this frame is not comparable with the photograph on proportion.** The camera was **not moved** — open air, azimuth clear for **150 m** against the 45.2 m needed — and the nearest built thing is `prop_lamp_cobra_davit_0` **9.0 m** away at 24.6° yaw and 22.5° pitch. Ground under the camera reads **6.261 m** NAVD88, the 10th percentile of **113** heightmap samples within 12 m, range 6.13 to 10.04 m.

**Sun** — azimuth 177.1°, elevation 40.9° at 2022-10-14T12:33:01−04:00, from the photograph's own **EXIF DateTimeOriginal**; 846.6 W/m² direct normal, sky at strength 0.0333, Filmic, **+5.99 stops**, and declared: *under-lit: the scene needed +5.99 stops to read as a picture, more than the 4 a photographer recovers hand-held*. The linear frame's median is **0.002829** against a target of 0.18; the physical rule would have given **+0.08 stops** (J83).

**In the scene** — 4,500,019 triangles: 6 building tiles (189,524 tris, none missing, none LOD-substituted), 7 landmark models of which 2 fall inside the 73.7° frame — **and neither is the subject** — 26,071 pavement polygons with **0 dropped**, 451 props, 6,765 kit pieces, 13 park-ground meshes over 127 surfaces, 3 structures tiles (64,904 tris), 77 vehicles and 254 people, terrain 79,386 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the record diagnoses this one itself, in a sentence worth quoting: "the line is open and the subject is not on it, which is a fault in the item's coordinate or in the model, not in the camera"

**The sightline found nothing where the subject should be.** Of 13 rays, **2 are clear and 2 pass into nothing**; the other eleven stop at **14.3 m** on `prop_tree_honeylocust_large_3`. Visible fraction **0.000**. And the record does not shrug: *nothing stands within 25 m of the subject's recorded coordinate on any clear ray: the clear rays meet nothing at all out to 550 m.* That is the strongest self-diagnosis in the pass — the chain distinguishing a blocked view from a missing subject, and saying which one it has.

**The probe, meanwhile, measured 236.88 m over 43 of 43 rays** on `lm_c_hudson_yards.40`, extent **69.3 m by 64.6 m**, with the nearest catalogue origin **205.1 m** away and correctly refused (J74). So there is fabric at the coordinate when probed from above it, and nothing on the bearing from the camera. Those two facts together locate the fault: the coordinate and the model do not agree about where this tower stands, which is what the record says.

**The render is otherwise the best-looking frame in this queue.** 189 of 226 trees drawn from modelled branches give a real street canopy with real shadows on the pavement; two towers rise out of the top of the frame; pedestrians walk on surveyed sidewalk. **And it carries a visible geometry break**: a pale green park surface climbs steeply across the right of the frame and meets the sidewalk along a hard edge, with a black gap open along the diagonal where the two surfaces separate. The measurements name it: between 150 and 400 m the park surface sits under the terrain on **0.3087** of 447 samples, minimum **−2.941 m**; beyond 400 m the minimum is **−6.865 m** against a maximum of **+6.137 m** (J85). Within 150 m the same surface is almost perfect — **0.0116** of 346 samples under, median **+0.192 m** — so the break is at the band boundary, where the terrain grid coarsens from 2 m to 40 m.

**The props budget cut this scene to an eighth.** 451 placed of **3,552 in range**: **2,818 dropped for the triangle budget** of 1,226,702 and 79 dropped on a suppressed building. Every tree that is drawn is drawn well, and seven eighths of the street furniture is not there.

## What matches

* **The record's diagnosis is exactly right and rare**: a blocked ray and an absent subject are different faults, and this sheet says which it has and why.
* **The height came from the geometry with the reason recorded**: 236.88 m, 43 of 43 rays, catalogue origin 205.1 m away and refused (J74).
* **The canopy is the best in the pass**: **189 of 226** trees from modelled branches, mean scale **0.946**, **0** out of band, and their shadows fall across the pavement.
* **Near-field ground is sound**: within 150 m, **0.0116** of 346 samples under the terrain, median **+0.192 m**.
* **The pavement is complete**: 26,071 polygons, **0 dropped**, including 12,164 white markings, 5,133 roadbed, 3,904 sidewalk, 3,046 curb and 756 parking lot.
* **The median tone matches**: **0.4948** against **0.5034** (**0.983×**), with the two development offsets **0.054 stops** apart — the closest pairing in this queue (J83).
* **Agents carry mixed detail**: 3 vehicles at LOD1, and of 254 people **34 at LOD1 and 6 at LOD0**.

## What does not match

* **The subject is not on the line.** Visible fraction **0.000**, 2 clear rays meeting nothing out to 550 m.
* **Neither landmark the frustum finds is the subject** — the Javits Center at 395.6 m and the Lincoln Tunnel at 1,092.9 m.
* **The frame is 5.99 stops under a photographable level**, declared as past hand-held recovery.
* **A park surface climbs over the sidewalk with a black gap along the join**, and the mid-band under-fraction of **0.3087** with a **−2.941 m** minimum is that break in numbers (J85).
* **Chroma is 0.324 of the photograph's**, 0.1066 against 0.3288 — the reference is a blue-glass tower against an October sky and the render has green canopy and grey asphalt.
* **The render is brighter and harsher**: mean **1.168×**, standard deviation **1.271×**, ninety-fifth percentile **0.9496** against 0.7421.
* **The top of the subject is cut off** at the 18 mm floor; the tower needs 69° of elevation at 90 m.
* **Seven eighths of the props are missing**: 451 placed of 3,552 in range, **2,818 dropped for the triangle budget** and 79 on a suppressed building, plus 3 impostor cards dropped.
* **All 226 trees had their species substituted** — the catalogue holds none of the species surveyed on this block.
* **6,765 of 33,226 kit records were drawn**, capped at a 1,193,191-triangle budget, with a further **11,697 suppressed** where a landmark shell stands in place of the tile's buildings.
* **All 3 structures tiles in range have no structures file** — over the Hudson Yards rail throat and the Lincoln Tunnel approach.
* **Park ground was not built for 1 tile** inside the 706 m ground radius, so that tile renders as bare terrain.
* **Forty-eight props across nine kinds were wanted in range and have no asset**: 30 misc structure, 7 drinking fountain, 4 artwork, 2 vending machine, 1 billboard, 1 memorial, 1 parks building, 1 parks comfort station, 1 passenger-information sign.
* **Four park-ground surface kinds fall back to the builder's flat colour** — sport court, park grass, recreation grass, bare ground (J40) — and one of them is the green surface breaking over the sidewalk.
* **The crowd is a ninth of the ask**: the table wanted 978 vehicles and 2,376 people; 1,169 and 2,637 were simulated and **3,475** dropped — 1,506 pedestrians and 646 vehicles outside the radius, 633 pedestrians and 411 vehicles at the agent triangle budget, 156 pedestrians in the carriageway without crossing, 81 not on a walkable surface, 16 vehicles not on a carriageway, 3 vehicles and 1 pedestrian inside a building, and **16 riderless bodies**.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the subject is not on the line, visible fraction 0.000 | the item's recorded coordinate and the model disagree about where this tower stands: the probe finds 236.88 m of fabric at the coordinate and the camera's clear rays meet nothing out to 550 m. The record states this as a fault in the coordinate or the model, not the camera — J89's family, a stored coordinate that cannot be used as it is | **data — open, one coordinate or one model** |
| a park surface over the sidewalk with a black gap | the terrain grid coarsens from 2 m to 40 m at 150 m, and the park surface keeps its survey shape across that boundary; the redrape moved 91,565 vertices and cannot close it (J85) | **geometry — open, measured** |
| +5.99 stops, under-lit | a north-facing street canyon in October; declared with its number rather than smoothed (J83) | verification — declared |
| chroma 0.324×, sd 1.271×, p95 0.9496 | no sky and no reflective curtain wall in the frame, and a hard midday sun on pale concrete | reference + consequence |
| the top of the subject is cut off | 18 mm is the widest lens the comparison allows and the subject needs 69° at 90 m | **verification — declared limit** |
| 451 props of 3,552 in range | the props triangle budget at 1,226,702, which dropped 2,818, plus 79 on a suppressed building | **performance** |
| 226 of 226 tree species substituted | the tree catalogue holds none of the species surveyed here | **data — open** |
| 6,765 kit pieces of 33,226 in range | the kit triangle budget at 1,193,191, plus 11,697 suppressed under landmark shells | performance + declared rule |
| 3 of 3 structures tiles without a file | no structures file was built for any tile in range | **data — open, three tiles unbuilt** |
| park ground missing on 1 tile | not built for that tile; the record names it | **data — open, one tile unbuilt** |
| 48 props across nine kinds unmapped | no asset exists for those kinds | data |
| four park surface kinds flat-coloured | the texture catalogue has no photographic set for any of them (J40) | **declared decision** |
| 254 people where the table asked 2,376 | the agent triangle budget plus the placement rules, each with its count | performance + verification |
