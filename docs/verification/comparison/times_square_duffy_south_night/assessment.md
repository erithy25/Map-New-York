# Times Square centre: Duffy Square looking south, night

`times_square_duffy_south_night` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Times Square, New York 02.jpg by Edward Charles Kendall, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2016-08-03 21:00:36, 1920x2560. [Commons page](https://commons.wikimedia.org/wiki/File:Times_Square,_New_York_02.jpg) — the view direction is derived from the image at **high** confidence. Nine in the evening in August, looking down the bowtie: several hundred people on the red steps and across the plaza, the Marriott Marquis carrying a full-colour campaign across four screens, thirty more lit faces on every wall, the Father Duffy memorial in silhouette, and the whole square lit to something close to daylight **by its advertising**.

**Camera** — 40.759086, -73.984856 (NYC_TM -2943, 6562) at z 21.5 m NAVD88, eye **6.2 m above the terrain** | azimuth 202.2°, pitch 0.0° | 24 mm on 36 mm (58.7° horizontal, 73.7° vertical, **portrait**) | 904x1206. The eye height is not the standing default and the record says why: *"top landing of the TKTS red steps at Duffy Square, 4.6 m above the plaza, plus 1.6 m eye height"* — the deck rule working (J65). The camera stands on **this photograph's own EXIF GPS**, **18.3 m** from the item's recorded viewpoint, whose azimuth it agrees with to **1.0°**. It was **not moved**: view azimuth clear for **150.0 m**, nearest built thing `prop_lamp_cobra_davit_5` at **16.3 m**, nearest simulated body `agent_ped_1996.8` at **18.0 m**. The ground under the lens reads 15.26 m NAVD88 from 16 samples within 5.0 m, range 15.08 to 16.36 m.

**Sun** — azimuth 302.7°, elevation **−9.5°** at 2016-08-03T21:00:36−04:00, from the photograph's own **EXIF DateTimeOriginal**; **0.0 W/m²** direct normal, sky at strength **0.5**, Filmic, **−1.25 stops**. This is a night frame and it is developed differently from every daylight sheet: `development.metered` is **false** and the stops are the physical rule's **−1.25**, not a measurement. Every emissive material is left as the kit authored it.

**In the scene** — 4,500,002 triangles: 6 building tiles (332,446 tris), 10 landmark models of which 1 falls inside the 58.7° cone, 31,276 pavement polygons, 2,779 props, 5,467 kit pieces, 22 park-ground meshes, **1 tile of structures (21,408 tris) with 5 having no file**, 53 vehicles and 248 people.

## Verdict — Times Square at night is lit by its advertising, and this build has no advertising, so the square is dark

**The render is black above the street lamps.** The upper two thirds of the frame carries almost no light at all: a few pale facade panels catching a lamp's cone, three or four narrow white vertical rectangles, and otherwise nothing. The photograph's upper two thirds is the brightest part of the picture. The measurement is exact about it: the render's 95th percentile is **0.4047** against the photograph's **0.9367**, and its standard deviation **0.1491** against **0.2522**, a ratio of **0.591**. The medians, by contrast, nearly agree — **1.072** — because the pavement and the crowd at the bottom of the frame are lit by street lamps in both halves. **What is missing is entirely in the highlights, and in this place the highlights are the subject.**

**The cause is declared and it is the whole sheet.** **249 billboard kit pieces** stand in this frame. Their faces carry named material slots and a defined 0..1 UV and **no content**: an LED face models the display hardware and a bulletin is blank vinyl, because no source in this environment records what a New York bulletin carries, and no advertising copy was invented anywhere (DEVIATIONS B5, B15, B15a). In daylight that costs the square its colour. **At night it costs the square its light.** The handful of white rectangles that do glow are the `TSQ_SCREEN_*` slots the Times Square builder places for the engine to bind a video to — emissive, unbound, and therefore rendering as blank white light rather than as a picture. The chroma ratio of **0.38** is the same fact measured a second way.

**The crowd is the other half of the photograph and it is not here either.** The density table asked for **4,637 people** — the largest ask on any sheet read this round — and **248** are drawn. 3,000 were simulated and **3,614 dropped**: 1,139 at the 1,125,000-triangle agent budget, 1,133 outside the radius, 323 in the carriageway without crossing, **150 not on a walkable surface**, 7 above the observer. Duffy Square's red steps, where the photograph's crowd is sitting, are not a road-network sidewalk class, so nobody sits on them (J101). A reader comparing the two halves sees a few dozen figures on a pavement against a plaza packed shoulder to shoulder.

**What the sheet gets right it gets exactly right.** The eye is on the top landing of the TKTS steps at **6.2 m**, because the item names a raised surface and the record honours it rather than standing an observer on the plaza (J65). The height probe refused the catalogue: the nearest entry 12.2 m away carries **365.8 m** — the Bank of America Tower's spire, a different building — and the probe measured **109.44 m** on `lm_c_times_square.32`, which is One Times Square's own roof height. Only **4 of 43** rays found fabric, which is what a fan around a tower standing behind screens does, and the record reports the ratio rather than hiding it. And the frame's own tonal centre is within a fifth of a stop of the photograph's: the render sits **2.942 stops below** the grey convention and the photograph **3.121 below**, a gap of **0.179 stops** — the closest exposure agreement of any night frame in this pass.

## What matches

* **The eye is on the steps.** 6.2 m above the terrain, from the TKTS structure's 4.6 m top landing plus a 1.6 m eye — the deck rule, stated with its source (J65).
* **The camera and heading are the photograph's own**, 18.3 m from the nominal viewpoint and agreeing with its azimuth to 1.0°.
* **The height is One Times Square's own roof.** 109.44 m measured, with the catalogue's 365.8 m correctly refused as a different member of the same composite (J74).
* **The exposure agreement is the closest of any night frame here**: a 0.179-stop gap, and a p50 ratio of 1.072.
* **The street lighting is modelled and visible.** Every emissive material is left as the kit authored it, and the two cobra lamps in the frame cast real cones onto the pavement — the lamps are the correct fixture for this block (J56).
* **The bowtie is paved as the bowtie**: 31,276 polygons with **14,390 white markings**, 6,005 sidewalk, 4,718 roadbed, 3,763 curb, **1,285 plaza**, 717 crosswalk and 311 median, and **0 dropped**.
* **The square is furnished for the crowd it gets**: 182 Citi Bike dock units, 134 cooling towers, 105 street lamps, 96 manholes, 58 hydrants, 24 vent grates, **18 LinkNYC kiosks**, 15 benches, 12 subway entrances, **10 newsstands**, 7 bike racks, 6 bus-stop signs and 4 steam vents.
* **Nothing was dropped for the props budget**: 2,779 placed of 2,899 in range.
* **The fleet is a Times Square fleet**: **22 yellow taxis** of 53 vehicles, with 10 boro taxis, 7 sedans, 7 SUVs, 5 black cars and 2 vans.
* **The day type is right**: 3 August 2016 was a Wednesday and the simulation used its weekday profile.

## What does not match

* **The square is dark.** 249 billboard pieces carry no content, so the light that makes this place is absent: 95th percentile 0.4047 against 0.9367, sd 0.591×, chroma 0.38×.
* **The screens that do glow are blank white.** The `TSQ_SCREEN_*` slots are emissive with no video bound, so they read as lit rectangles rather than as pictures.
* **248 people where the table asked 4,637**, and none of them on the red steps (J101).
* **The Father Duffy memorial is not legible** in the render, where it is the photograph's central silhouette.
* **No flag.** The photograph's American flag on its pole is a third of the frame's height; flags are not a class this build models.
* **The night frame is not metered.** `development.metered` is false and the development is the physical rule's −1.25 stops, so unlike every daylight sheet this frame's tone is assumed rather than measured (J83 applies to daylight only).
* **Eighty per cent of the kit was withheld.** 5,467 drawn of **26,779** in range against a **1,021,417**-triangle budget, of which 4,878 are windows and 249 billboards against **19 cornices**; a further **4,590** were suppressed under the landmark shells.
* **Eight trees in 2,098 are drawn from modelled branches**; 2,090 are six-triangle cards, and 813 of them are a substituted species (J108).
* **Structures are almost absent**: 1 tile imported for 21,408 triangles with **5 having no file**, over the Times Square–42nd Street interchange.
* **The render is darker overall**, mean 0.754×, and its 5th percentile is 0.012 against the photograph's 0.044 — the shadows are crushed where the photograph's are lifted by ambient advertising light.
* **The park ground sinks in the middle distance**: 0.3366 of 101 samples in the 150 to 400 m band, and 0.2479 across all 1,416. There are **0 samples within 150 m**.
* **Twenty-four props across five kinds had no asset**: 15 misc structure, 4 artwork, 3 vending machine, 1 memorial, 1 passenger-information sign. The memorial with no asset is the Duffy monument's own class.
* **The frustum reports the composite's centroid**: Times Square at 373.7 m and 36.0° off axis, while the camera stands inside the composite (J99).
* **Most agents are at the coarsest LOD**: 44 of 53 vehicles and 193 of 248 people at LOD2.

## Measured for this assessment

| figure | where it comes from |
|---|---|
| the closest exposure agreement of any night frame in this pass | the recorded `render_over_reference.exposure_offset_stops` of 0.179, compared across every record whose `night` flag is true |
| 109.44 m is One Times Square's own roof height | the recorded probe height against the building's published roof, and against the catalogue entry the probe refused, whose 365.8 m the Times Square builder's own note identifies as the Bank of America Tower's spire |
| the white rectangles are the TSQ_SCREEN slots | the `screen` material factory in `blender/landmarks/c_common.py`, which defines `TSQ_SCREEN_<n>` as an emissive material at strength 6.0 on a near-white base for the engine to bind a video texture to, with an exact 0..1 UV island per screen |
| the billboard faces carry named slots, a defined UV and no content | the `sign_face_binding` block of the tile's own `kit_placements.json` and the signage section of DATA_CONTRACTS: an LED face models the display hardware and a bulletin is blank vinyl, because no source records what a New York bulletin carries (DEVIATIONS B5, B15, B15a) |
| 4,637 is the largest crowd ask read this round | the density table figure in this record, against the forty-one sheets read in the preceding rounds |
| the TKTS steps' top landing is 4.6 m above the plaza | the eye-source field of this record, and the 27 steps rising 4.9 m in `blender/landmarks/c_times_square.py` |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the square is dark | 249 billboard pieces are placed with named material slots, defined UVs and no content, because no advertising copy was invented anywhere. In daylight that costs the square its colour; at night it costs the square its light, which is the whole subject of this frame | **declared decision — the slots and UVs exist; the runtime content binding is the open half (B15a)** |
| the screens that glow are blank white | `TSQ_SCREEN_<n>` is an emissive slot at strength 6.0 awaiting a video texture from the engine | **declared decision — same half** |
| 248 people where the table asked 4,637, none on the steps | the 1,125,000-triangle agent budget plus the placement rules; the red steps are not a road-network sidewalk class, so 150 bodies were dropped for not standing on one (J101) | **performance + verification** |
| the Duffy memorial is not legible and no monument asset exists | no asset exists for the memorial or artwork kinds, so the plaza's monuments are absent (J58 remainder) | data — open |
| no flag | flags are not a class this build models | geometry — no source |
| the night frame is not metered | night development is the physical rule at -1.25 stops rather than a measurement of the frame, because a night scene's median is not a photographable-level target (J83) | **declared decision** |
| the kit withheld — 5,467 drawn of 26,779 in range — and 19 cornices drawn | the kit triangle budget at 1,021,417 triangles, plus 4,590 pieces suppressed under the landmark shells | performance |
| 8 modelled tree canopies in 2,098, 813 substituted species | only 8 rows fall within the 120 m branch band, and the asset set is ten species with two states (J108) | performance + data |
| 21,408 triangles of structures over the busiest interchange in the system | five of the six tiles in range have no structures file (B13 remainder) | **data — open** |
| park ground under the terrain in the middle distance | the park surfaces were draped on the fine grid and the terrain coarsens to 40.0 m (J40, J96) | verification — declared |
| the frustum names the composite's centroid | a composite landmark is tested by its centroid, and this camera stands inside the composite (J99) | verification — open |
