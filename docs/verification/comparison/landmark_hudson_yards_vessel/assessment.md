# Hudson Yards and the Vessel

`landmark_hudson_yards_vessel` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:The Vessel October 2022 006.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-10-14 12:16:07, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:The_Vessel_October_2022_006.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.753074, -74.00204 (NYC_TM -4395, 5895) at z 8.7 m NAVD88 | azimuth 350.5°, pitch +0.4° | 24 mm on 36 mm (74.4° horizontal) | 1208x906. The camera stands on **the item's recorded viewpoint**, not the photograph's: this photograph's own EXIF GPS is **71 m** away and the eye point there is **inside `lm_c_hudson_yards.44`** — a ray straight up from it hits that roof — while the recorded viewpoint is in open air. The recorded azimuth of 350.5° agrees with the bearing to the Vessel from the position used to **0.0°**. The lens was **widened from 35 mm to 24 mm** so that a level axis could contain the subject, and the axis was still tilted **+0.4°**: the top of `t_-5_5_roof_membrane`, the built thing standing at the subject's coordinate, stands 41 m above the lens at 82 m, **26° above the horizon**, against a frame only 59° tall. **The verticals converge, so this frame is not comparable with the photograph on proportion.** Eye height 1.6 m above the terrain surface. The clearance walk did **not** move the camera: `offset_m` 0.0, the view azimuth clear for **59 m** against the 40.9 m the frame needs, the nearest built thing `prop_tree_honeylocust_medium_29` **1.8 m** away at 24.8° right of axis, and no simulated agent within 60 m.

**Sun** — azimuth 171.6°, elevation 40.6° at 2022-10-14T12:16:07−04:00, from the photograph's own **EXIF DateTimeOriginal**; 844.8 W/m² direct normal, sky at strength 0.0334, Filmic, **+6.00 stops, clamped**. The linear frame's median is **0.000349** against a middle-grey target of 0.18, so the meter asked for **+9.01 stops** and the development held at the ceiling of 6. The record says why in its own words: *a scene this far from a photographable level is not developed into a picture of one*. The physical rule would have given **+0.09 stops**.

**In the scene** — 4,041,241 triangles: 4 building tiles (189,114 tris, none missing, none LOD-substituted), 5 landmark models of which 3 fall inside the 74.4° frame, 20,730 pavement polygons, 946 props, 6,188 kit pieces, 12 park-ground meshes over 125 surfaces, 2 structures tiles (40,632 tris), 88 vehicles and 432 people, terrain 73,196 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the Vessel is not in this frame, and the record says so before the eye does: 0 of 13 sightline rays reach it, so the visible fraction is **0.000**

**This sheet compares a photograph of the Vessel against a picture of something else.** The left half is the sculpture filling two thirds of the image behind the glass curtain of 35 Hudson Yards. The right half is a dark interior-looking volume: a heavy overhead mass with a straight lower edge, four round columns, a pale polished plaza floor, and one slot of daylight at the upper left. The record names the two things standing at that range — **`lm_c_hudson_yards.51`, the shell that stops the ray to the subject **7.4 m** out**, and `prop_tree_honeylocust_medium_29` 1.8 m off the lens — and either way the subject is behind them.

**The measurement agrees with the picture, which is the one good thing here.** Of 13 rays cast at the subject's mid-height, 19.0 m above its ground: **0 clear, 0 on the subject, 0 into nothing**, blocked at 7.4 m. `subject_visible` is **False** and `subject_visible_fraction` is **0.000** under the stated rule that at least one ray must land on the subject (J78). The sheet is published with that verdict on its face rather than as a near miss.

**The exposure is the second half of the same story.** A frame whose median linear luminance is **0.000349** — a five-hundredth of middle grey — is not an under-lit picture of Hudson Yards, it is the inside of something. The meter asked for nine stops and the clamp refused; the render still arrives at mean **0.1923** against the photograph's **0.3025** and chroma **0.0419** against **0.0900**, a ratio of **0.466**.

## What matches

* **The height probe is the cleanest in this pass**: **43 rays cast, 43 landing on built fabric**, giving 38.43 m above a ground of 10.95 m NAVD88 at the subject's coordinate. That is the podium level of the Eastern Yard, measured off the object at the recorded coordinate rather than taken from the catalogue (J74) — the catalogue's nearest origin, `c_hudson_yards` at 113.4 m, carries 387.1 m and was correctly not used.
* **The median tone is nearly the photograph's** — **0.1699** against **0.1816**, a ratio of **0.936** — which is what the metered development is for: two frames of very different content brought to the same grey (J83).
* **The camera stands where it can stand.** The recorded viewpoint passed the open-air test and the photograph's own GPS did not; choosing the one in open air over the one inside a building shell is the right call, and the record states both positions and the 71 m between them.
* **The pavement under the square is fully drawn**: 20,730 polygons, **0 dropped**, of which 8,515 are white markings, 4,705 roadbed, 3,806 sidewalk, 2,412 curb, 382 crosswalk and 275 plaza.
* **Near-field ground is sound.** Within 150 m, **99.8 %** of the park surface clears the terrain — median +0.20 m over 508 samples, minimum −0.027 m, z-fighting fraction 0.002.
* **Trees are placed from their own survey and scaled**: 371 drawn, mean scale **0.963** with **0** instances out of band, and 360 species substitutions recorded rather than hidden.
* **The crowd is this hour's crowd, not a decoration**: 432 people and 88 vehicles from one frame of the simulation at seed 20260907 after 120 s, on a weekday profile for a Friday.

## What does not match

* **The subject is absent.** Visible fraction **0.000**, 0 of 13 rays, blocked 7.4 m from the lens. No other measurement on this sheet can compensate for that.
* **The frame is nine stops from a photographable level** and was published at the six-stop ceiling, so the render reads as a dark interior where the photograph reads as noon.
* **The verticals converge** at +0.4° on a 24 mm lens, and the record says outright that proportion is not comparable here.
* **Contrast is half the photograph's** — standard deviation **0.1369** against **0.2680**, a ratio of **0.511** — because a clamped dark frame has nowhere to put its range.
* **Chroma is 0.466 of the photograph's.** The reference's copper lattice against a blue October sky is the most saturated thing in the neighbourhood, and none of it is in the frame.
* **Two structures tiles in range have no structures file** — 2 of 2 — on a block built over the Hudson Yards rail throat, the one place in the city where the railway under the platform is the reason the platform exists.
* **Mid-field ground is the worst band on this sheet**: between 150 and 400 m the park surface sits **under** the terrain on a fraction of **0.2463** of 954 samples, by more than 5 cm on **0.2296**, minimum **−9.54 m**, and the redrape moved 77,164 vertices by up to 3.29 m to get that far (J85).
* **965 tree rows in range did not fit the props budget**, and 3 impostor cards were dropped; **0** of the 218 cards are procedural canopy stems, so the woodland rule contributes nothing here.
* **Twenty-six props across eight kinds were wanted in range and have no asset**: 10 misc structure, 7 drinking fountain, 4 artwork, 1 billboard, 1 memorial, 1 parks building, 1 passenger-information sign, 1 vending machine.
* **The crowd is a fifth of the ask.** The density table wanted **873 vehicles and 1,806 people**; 1,087 and 2,937 were simulated and **3,504** dropped — 605 pedestrians and 376 vehicles at the agent triangle budget, 1,607 and 588 outside the radius, 213 pedestrians in the carriageway without crossing, 77 not on a walkable surface, 3 inside a building, and **19 riderless bodies** (cyclists, e-bikes, pedicabs the fleet exports without a rider).
* **Every agent is LOD2**: 88 vehicles and 432 people, none at a nearer level of detail.
* **Four park-ground surface kinds fall back to the builder's flat colour** — sport court, park grass, recreation grass, bare ground — because the texture catalogue holds walls, roofs, roadway and floors and no photographic set for any of them (J40).
* **The frustum reports Hudson Yards (Eastern Yard) 35.1° off axis** at 106.8 m, which is the composite's centroid rather than the Vessel.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the subject is not in the frame, visible fraction 0.000 | the clearance walk passed the recorded viewpoint on the open-air test at eye level and never weighed what stands in front of the subject; `lm_c_hudson_yards.51` closes the sightline 7.4 m out while the azimuth is clear for 59 m at 1.6 m. This is J87's family: walk and deck rule each correct, composing into a frame with no subject in it | **verification — open, J87** |
| +6.00 stops, clamped, against +9.01 asked | the scene the walk chose is a dark volume, so the meter's honest answer exceeds the ceiling; the clamp is the declared behaviour (J83) and the dark frame is J87's consequence | verification — declared clamp, open cause |
| verticals converge | 24 mm and +0.4° were needed to contain a subject 26° above the horizon at 82 m; the record states proportion is not comparable rather than implying it is | **verification — declared** |
| sd 0.511×, chroma 0.466× | a clamped dark frame with no sky and no copper in it | consequence of the two rows above |
| 2 of 2 structures tiles without a file | no structures file was built for either tile in range, over the Hudson Yards rail throat | **data — open, two tiles unbuilt** |
| an under-fraction of 0.2463 in the mid field, min −9.54 m | the terrain grid coarsens to 40 m beyond the near band while the park surface keeps its survey shape; the redrape closes the near field and cannot close the mid field (J85) | **geometry — open, measured** |
| 965 tree rows dropped, 0 canopy stems | the props triangle budget at 1,319,834 triangles; the woodland canopy rule places stems only inside mapped woodland polygons and this square has none | performance + declared rule |
| 26 props across eight kinds unmapped | no asset exists for those kinds | data |
| four park surface kinds flat-coloured | the texture catalogue has no photographic set for court, grass or bare ground, and the builder's colour is kept rather than the nearest wrong material (J40) | **declared decision** |
| 432 people where the table asked 1,806 | the agent triangle budget plus the placement rules, each with its count | performance + verification |
| every agent at LOD2 | the LOD rule picks by distance and the crowd in range sits beyond the nearer bands | performance |
| Eastern Yard reported 35.1° off axis | the frustum test uses a landmark composite's centroid, not the piece being looked at | verification |

## What this sheet is good for

Not for judging the Vessel. It is the clearest single demonstration in the pass that **the verification chain can produce a certified frame with no subject in it**, and that the chain's own numbers catch it: a visible fraction of 0.000, a nine-stop meter reading, and a 43-of-43 height probe that measures the podium the camera is standing under. J87 is recorded against it. Until that is repaired, this sheet's honest content is the measurement, not the picture.
