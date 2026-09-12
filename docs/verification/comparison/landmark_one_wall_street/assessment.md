# One Wall Street (Irving Trust Building)

`landmark_one_wall_street` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Buildings in FiDi, Manhattan.jpg by Emperor of Emperors, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2026-02-27 15:49:02, 1920x2560. [Commons page](https://commons.wikimedia.org/wiki/File:Buildings_in_FiDi,_Manhattan.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.70679, -74.01239 (NYC_TM -5289, 757) at z 11.2 m NAVD88 | azimuth 52.0°, pitch +28.9° | 18 mm on 36 mm (73.7° horizontal, 90.0° vertical, portrait) | 904x1206. Position and heading both come from the photograph: its own EXIF camera GPS, **32.5 m** from the item's recorded viewpoint, and 52.0° is the bearing from there to the subject. The item's recorded azimuth of 75.0° is **23.0° away** and belongs to its nominal viewpoint. The lens was **widened from 35 mm to the 18 mm floor** and the axis tilted **+28.9°**, and even then the top of the subject is cut off: `lm_one_wall_street.2` stands 197 m above the lens at 78 m, **68° above the horizon**, against a 90° frame. **The verticals converge, so this frame is not comparable with the photograph on proportion.** The recorded viewpoint was **boxed in** — the view azimuth closed off **25 m** ahead against the **38.8 m** this frame needs — so the camera was **moved 14.9 m** onto the nearest roadbed polygon, and the walk scored that choice on the subject's own sightline (`scored_on_subject_sightline` true, 8 of 13 rays on the subject at the point chosen). Ground under the camera reads **9.643 m** NAVD88, the 10th percentile of **113** heightmap samples within 12 m, range 9.52 to 9.99 m.

**Sun** — azimuth 239.6°, elevation 19.8° at 2026-02-27T15:49:02−05:00, from the photograph's own **EXIF DateTimeOriginal**; 649.3 W/m² direct normal, sky at strength 0.0408, Filmic, **+6.00 stops, clamped**. The linear frame's median is **0.001781** against a middle-grey target of 0.18, so the meter asked for **+6.66 stops** and the development held at the ceiling of 6. The physical rule would have given **+1.14 stops** — a five-stop gap, and the reason a February late afternoon at 19.8° elevation inside a FiDi canyon cannot be developed into a picture of one.

**In the scene** — 4,500,129 triangles: 4 building tiles (106,490 tris, none missing, none LOD-substituted), 10 landmark models of which 6 fall inside the 73.7° frame, 23,421 pavement polygons with **0 dropped**, 1,143 props, 4,895 kit pieces, 19 park-ground meshes over 278 surfaces with **53,345 faces cut** where a landmark supplies its own ground, 3 structures tiles (43,576 tris), 84 vehicles and 290 people, terrain 80,914 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the top three fifths of this render is a credible Financial District canyon; the bottom two fifths is black, and nothing in the record says what put it there

**The measured comparison is good where the frame has content.** The subject is found and measured exactly: 43 of 43 probe rays land on built fabric, giving **200.18 m** above a ground of 7.96 m at the subject's coordinate, against the catalogue's **199.3 m** for `one_wall_street` 13.3 m away — **0.88 m apart**, the closest agreement between probe and catalogue on any landmark sheet in this pass. The sightline finds it too: 13 rays, **12 clear**, **8 on the subject**, visible fraction **0.615**. The median tone matches the photograph almost exactly, **0.4111** against **0.4054** (**1.014×**).

**Then the frame fails below row 719 of 1206.** I measured it off the image: **0.4056 of the render is below a luminance of 0.004** — effectively zero — and the bottom **487 rows are each more than 98 % black**, cut off by a razor-straight horizontal boundary. The development record already shows it from the other side: `linear_p05` is **0.0** and the published p05 is **0.0**, while the photograph's is 0.1123. Immediately above that boundary, **0.2205 of the frame is green-dominant**, and its bounding box ends at row 718 — the same line. Something large, green where the low sun catches it and unlit below its edge, stands close enough to the lens to take two fifths of the picture.

**The render record cannot name it, and that is the finding.** Every geometric claim in the record is about the path from the lens to the subject: the clearance walk measures the view azimuth (clear for 60 m), the nearest built thing in the frame (`t_-6_0_terracotta`, 13.1 m at −36.9°), and 13 rays at the subject. **Nothing measures what fills the frame.** So a sheet can be certified with a visible fraction of 0.615 while two fifths of it is an unnamed occluder. That is a new fault in the verification chain, recorded as **J92**, and it is bounded: across 167 rendered frames, **5** carry more than 5 % near-black pixels, this one worst at 0.4056.

## What matches

* **The probe and the catalogue agree to 0.88 m** — 200.18 m measured off `lm_one_wall_street.2` at the recorded coordinate against 199.3 m in the catalogue entry 13.3 m away. The height was measured off the object, not read from the entry (J74), and the two independently say the same thing.
* **The clearance walk did its job properly here.** It refused a viewpoint boxed in at 25 m, moved 14.9 m onto real surveyed roadbed, and scored the destination on the subject's sightline rather than on eye-level clearance (J79) — the record carries `subject_sightline_at_choice` with the 8-of-13 result it accepted.
* **The median tone is the photograph's**, 0.4111 against 0.4054, and the two exposure offsets from the grey convention are **−0.354** and **−0.397** stops — **0.043 stops apart**, the closest pairing in the pass (J83).
* **The canyon is right in kind.** Both halves are a narrow street walled by deep window grids, with a fluted tower closing the view; the render's six in-frame landmarks — One Wall Street at 75.8 m, the Stock Exchange at 116.9 m, Trinity Church at 143.4 m, Federal Hall at 205.7 m, the Equitable Building at 236.0 m and 40 Wall Street at 244.3 m — are the six things that are actually in that view.
* **The pavement is complete**: 23,421 polygons, **0 dropped**, including 7,796 white markings, 5,518 sidewalk, 4,894 roadbed, 3,703 curb, 515 crosswalk and 502 plaza.
* **Near-field ground is sound**: within 150 m, the park surface clears the terrain on all but **0.0226** of 266 samples, median **+0.187 m**, minimum −0.098 m.
* **The landmark-ground rule is doing real work here** — **53,345 park-ground faces and 347 terrain quads cut** where a landmark supplies its own ground, the largest cut on any sheet in the pass.
* **Agents are at mixed detail rather than all-distant**: 1 vehicle at LOD1, and of 290 people **43 at LOD1 and 1 at LOD0**.

## What does not match

* **Two fifths of the frame is black.** Measured at **0.4056** of pixels below luminance 0.004, the bottom **487** rows more than 98 % black, boundary straight and horizontal at row **719** of 1206, and the photograph's darkest fifth percentile is 0.1123; the render's is **0.0**.
* **A green surface takes the fifth above that line** — **0.2205** of the frame is green-dominant, bounded at row 718. Green at this position in the Financial District has no referent in the photograph: there is no lawn, no planting and no green roof in that view.
* **The record names no occluder.** The clearance walk reports the azimuth clear for 60 m and the nearest built thing 13.1 m away at −36.9°; neither accounts for an object across the lower frame.
* **Contrast is 1.564× the photograph's** — standard deviation **0.3199** against **0.2045** — and that number is not a richer picture, it is the distance between a blown 0.9068 p95 and a black floor.
* **Chroma is 0.646 of the photograph's**, 0.0567 against 0.0878.
* **The top of the subject is cut off** at the 18 mm floor, so the crown that closes the photograph's view is not in the render's frame at all.
* **A street lamp is across the sightline.** The nearest thing blocking a ray to the subject is `prop_lamp_cobra_davit_0` at **21.8 m** — the clearance walk weighs built fabric and does not weigh a cobra-head mast (J88), and 7 of the 13 rays land on the subject's own fabric nearer than the recorded coordinate while 4 pass into nothing.
* **A simulated pedestrian stands 1.4 m from the lens.** `agent_ped_1651.10` is inside the 8 m of nothing-built the walk enforces against geometry and never applies to the crowd (J91).
* **+6.00 stops, clamped, against 6.66 asked** — the frame is published two thirds of a stop under its own meter, and five stops above what the physical rule would have given.
* **One of 3 structures tiles in range has no structures file**, under the Broadway and Wall Street subway interchange.
* **Beyond 400 m the park surface sits under the terrain on 0.2727 of 484 samples**, minimum **−3.41 m**, and the redrape had already moved **188,467** vertices by up to 2.449 m.
* **19 trees are drawn from modelled branches and 152 are impostor cards**, with **0** procedural canopy stems and **2,426 tree rows** that did not fit the props budget of 1,200,820 triangles; 3 impostor cards were dropped and **1** tree instance scaled out of band.
* **27,824 kit records were in range and 4,895 were drawn**, capped at a 1,146,769-triangle budget.
* **Twenty props across four kinds were wanted in range and have no asset**: 8 artwork, 8 memorial, 3 drinking fountain, 1 misc structure.
* **The crowd is a fifteenth of the ask.** The density table wanted **780 vehicles and 4,545 people**; 942 and 2,999 were simulated and **3,560** dropped — 1,462 pedestrians and 594 vehicles outside the radius, 837 pedestrians and 214 vehicles at the agent triangle budget, 295 pedestrians in the carriageway without crossing, 78 not on a walkable surface, 19 inside a building, 18 above the observer, 18 vehicles inside a building, 9 not on a carriageway, and **22 riderless bodies**.
* **Eight park-ground surface kinds fall back to the builder's flat colour** — infield dirt, cemetery grass, sport court, greenstreet grass, park grass, pool water, recreation grass, bare ground — because the texture catalogue holds walls, roofs, roadway, floors and vehicle interiors and no photographic set for any of them (J40).

## Cause of each gap

| gap | cause | class |
|---|---|---|
| 0.4056 of the frame black, boundary straight at row 719 | an unnamed surface close to the lens fills the lower frame; the record measures only the path to the subject, so nothing in it identifies what occludes the rest. New fault **J92**; 5 of 167 rendered frames carry more than 5 % near-black pixels | **verification + geometry — open, J92** |
| 0.2205 of the frame green-dominant, ending at the same row | the lit face of that same surface; green has no referent in this view | **open, same object as the row above** |
| sd 1.564×, chroma 0.646×, p05 0.0 | the black floor and the 0.9068 p95 in one frame | consequence of J92 |
| the subject's crown is cut off | 18 mm is the widest lens the comparison allows; past it the distortion would stop the two frames being comparable, and the subject needs 68° of elevation at 78 m | **verification — declared limit** |
| a cobra-head mast 21.8 m across the sightline | the clearance walk clears built fabric and does not weigh street lamps (J88) | verification — open |
| a pedestrian 1.4 m from the lens | the 8 m nothing-built rule applies to geometry and not to the crowd (J91) | verification — open |
| +6.00 stops, clamped | median linear 0.001781 against a 0.18 target in a February canyon at 19.8° sun elevation; the clamp is declared (J83) | verification — declared |
| 1 of 3 structures tiles without a file | no structures file was built for that tile | **data — open, one tile unbuilt** |
| 0.2727 of far park ground under the terrain, min −3.41 m | the terrain grid coarsens to 40 m beyond the near band while the park surface keeps its survey shape (J85) | geometry — open, measured |
| 2,426 tree rows dropped, 0 canopy stems | the props triangle budget at 1,200,820 triangles; no mapped woodland polygon in this radius | performance + declared rule |
| 27,824 kit records in range, 4,895 drawn | the kit triangle budget at 1,146,769 | performance |
| 20 props across four kinds unmapped | no asset exists for those kinds | data |
| eight park surface kinds flat-coloured | the texture catalogue has no photographic set for any of them, and the builder's colour is kept rather than the nearest wrong material (J40) | **declared decision** |
| 290 people where the table asked 4,545 | the agent triangle budget plus the placement rules, each with its count | performance + verification |

## Measured for this assessment

Four figures above are not in the render record. The record measures the path from the lens to the
subject and never measures what fills the frame, which is the gap this sheet exposes, so I measured
the frame itself. Read with `docs/verification/comparison/landmark_one_wall_street/render.png`
(904x1206) and, for the survey row, every `render.png` under `docs/verification/comparison`,
luminance as 0.2126 R + 0.7152 G + 0.0722 B on the 8-bit sRGB values.

| figure | where it comes from |
|---|---|
| 0.4056 | fraction of the render's pixels with luminance below 0.004 |
| 0.88 | 200.18 m, the probe's measured height, minus the 199.3 m the catalogue entry `one_wall_street` carries |
| 719 | first image row that is more than 98 % below that threshold; 487 such rows run to the bottom edge at 1205 |
| 0.2205 | fraction of pixels whose green channel exceeds both others by more than 0.04, bounding box rows 0 to 718, columns 94 to 903 |
| 5 | rendered frames of 167 whose near-black fraction exceeds 0.05: this one at 0.4056, the Parachute Jump at 0.3332, the Shed at 0.1010, SoHo cast iron at 0.0599, the Woolworth Building at 0.0576 |
