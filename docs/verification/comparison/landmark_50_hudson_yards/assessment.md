# 50 Hudson Yards

`landmark_50_hudson_yards` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:50 Hudson Yards.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2023-02-18 12:42:25, 1280x1707. [Commons page](https://commons.wikimedia.org/wiki/File:50_Hudson_Yards.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.75434, -73.99763 (NYC_TM -4000, 6007) at z 16.0 m NAVD88 | azimuth 270.0°, pitch +16.2° | 18 mm on 36 mm (73.7° horizontal, 90.0° vertical, portrait) | 904x1206. The camera stands on **the item's recorded viewpoint**: this photograph's own EXIF GPS is **298.4 m** away, past the 250 m at which it could still be the same view. The recorded azimuth of 270.0° agrees with the bearing to the subject to **0.0°**. The lens was **widened from 35 mm to the 18 mm floor** and the axis tilted **+16.2°**, and the top of the subject is still cut off: `lm_c_hudson_yards.35` stands 295 m above the lens at 200 m, **56° above the horizon**. **The verticals converge, so this frame is not comparable with the photograph on proportion.** The recorded viewpoint was **inside `t_-5_6_roof_membrane`**, so the camera was **moved 34.4 m** onto the nearest surveyed sidewalk polygon, scored on the subject's sightline — which at the chosen point returned **1 of 13 rays**, visible fraction 0.077, and was still the best available. From there the view azimuth is clear for **96 m** and the nearest built thing is `prop_lamp_cobra_davit_14` **16.6 m** away at −36.9°. Ground under the camera reads **14.432 m** NAVD88, the 10th percentile of **113** heightmap samples within 12 m, range 13.43 to 15.33 m.

**Sun** — azimuth 190.0°, elevation 37.2° at 2023-02-18T12:42:25−05:00, from the photograph's own **EXIF DateTimeOriginal**; 824.5 W/m² direct normal, sky at strength 0.0341, Filmic, **+5.00 stops**. The record declares the consequence rather than hiding it: *under-lit: the scene needed +5.00 stops to read as a picture, more than the 4 a photographer recovers hand-held; the frame is published and this is the number to read it by*. The linear frame's median is **0.00564** against a target of 0.18; the physical rule would have given **+0.21 stops** (J83).

**In the scene** — 4,500,093 triangles: 4 building tiles (189,114 tris, none missing, none LOD-substituted), 7 landmark models of which 3 fall inside the 73.7° frame, 31,295 pavement polygons with **0 dropped**, 2,506 props, 5,735 kit pieces, 12 park-ground meshes over 125 surfaces, 2 structures tiles (40,632 tris), 69 vehicles and 397 people, terrain 87,128 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the camera was snapped onto a sidewalk that has a shed over it, so a 300-metre tower is behind a plywood deck four metres above the lens

**The render is the underside of a sidewalk shed.** Green steel posts and beams carry a plywood deck across the upper half of the frame; beyond them a brick tenement block with fire escapes, a pale sidewalk and a handful of pedestrians. It is a good sidewalk shed — the posts, the cross-beams, the deck boards and the shop fronts beyond all read correctly, and there are 108 scaffold pieces in range to build it from. It is not a picture of 50 Hudson Yards.

**The walk's rule is horizontal and the subject is vertical.** The record's clearance test says the view azimuth is clear for **96 m**, which is true at eye level, and the subject needs **56° of elevation** at 200 m. A shed deck about four metres up cuts everything above roughly twenty degrees. The sightline then found what the picture shows: 13 rays, **3 clear**, **1 on the subject**, blocked at **25.5 m** by `t_-5_6_red_brick`, visible fraction **0.077** — and the walk accepted that point because it was the best of the set it scored (J79 working as specified, on a specification that does not test the vertical). This is J87's family with a specific and common cause: **a sidewalk snap under a shed.**

**The height itself is measured properly.** `lm_c_hudson_yards.35`, **300.9 m** above a ground of 9.33 m, **43 of 43** rays on built fabric, plan extent **101.8 m by 83.4 m**. The catalogue origin 118.5 m away carries 387.1 m for the whole composite and was not used for this member (J74).

**The tonal comparison runs the other way from most of this pass.** The render is **brighter** than the photograph: mean **0.5566** against **0.3583** (**1.553×**), median **0.4964** against **0.3284** (**1.512×**). The photograph's own development sits **1.031 stops below** the grey convention and the render's **0.227 above** it, a **1.258-stop** difference — a dark blue glass tower photographed against a February sky is a genuinely dark picture, and the render's frame is a pale sidewalk under a shed.

## What matches

* **The sidewalk shed is convincing.** Posts, beams, deck, and the fire-escaped brick block beyond are the right fabric for West 33rd Street, and this is the clearest view of the scaffold kit anywhere in the pass.
* **The height probe is complete and the extent is real**: 43 of 43 rays, 300.9 m, extent 101.8 m by 83.4 m measured off the object (J74).
* **The under-lit frame is declared with its number**, not smoothed: +5.00 stops, and the record says that is past what a photographer recovers hand-held (J83).
* **The clearance walk caught a viewpoint inside a roof membrane** and moved to real surveyed sidewalk, scoring candidates on the subject's sightline (J79).
* **The day type is right and was read**: the crowd clock reads **Saturday** for 2023-02-18, which was a Saturday.
* **The season is right**: props are placed with **bare canopies** for February, and the render's one street tree is bare.
* **The woodland canopy rule contributes**: **53** of the 1,638 impostor cards are procedural canopy stems placed inside mapped woodland polygons.
* **The pavement is complete**: 31,295 polygons, **0 dropped**, including 14,437 white markings, 5,860 roadbed, 4,894 sidewalk, 3,980 curb, 901 crosswalk and 532 median.
* **48 of 1,686 trees are drawn from modelled branches**, the rest as cards.

## What does not match

* **The subject is behind a shed deck.** Visible fraction **0.077**, 1 of 13 rays, blocked at 25.5 m.
* **The frame is 5.00 stops under a photographable level**, which the record itself calls past hand-held recovery.
* **The render is 1.553× the photograph's mean and 1.512× its median** — brighter, not darker, because the two frames contain different things at different exposures (1.258 stops of development apart).
* **Chroma is 0.31 of the photograph's**, 0.0874 against 0.2821. The reference is one deep blue reflective curtain wall; the render has brick, plywood and concrete.
* **The top of the subject is cut off** at the 18 mm floor, and so is all of it in practice.
* **There is no park ground within 150 m to check** — **0 samples**. Between 150 and 400 m the park surface sits under the terrain on **0.336** of 988 samples, minimum **−5.066 m**, against a maximum clearance of **+12.091 m** in the same band: a 17-metre spread across the platform edge (J85).
* **Both structures tiles in range have no structures file** — 2 of 2 — over the rail yard.
* **12,315 kit records were in range and 5,735 were drawn**, capped at a 1,338,391-triangle budget.
* **Props were not capped here** — 2,614 rows in range and 2,506 placed, 0 dropped for the budget, 1 dropped on a suppressed building — but 11 impostor cards were dropped, **879 of 1,686** tree species were substituted, and **4** tree instances were scaled out of band.
* **Twenty-three props across four kinds were wanted in range and have no asset**: 20 misc structure, 1 artwork, 1 memorial, 1 passenger-information sign.
* **Four park-ground surface kinds fall back to the builder's flat colour** — sport court, park grass, recreation grass, bare ground (J40).
* **The frustum names the Hudson Yards composite 2.6° off axis at 348.6 m** while the subject is 223.8 m away: the composite's centroid, 125 m beyond the member aimed at.
* **The crowd is an eighth of the ask**: the table wanted 829 vehicles and 3,312 people; 974 and 3,000 were simulated and **3,507** dropped — 779 pedestrians and 521 vehicles outside the radius, 767 pedestrians and 347 vehicles at the agent triangle budget, **729 pedestrians in the carriageway without crossing**, 323 not on a walkable surface, 19 vehicles not on a carriageway, 4 inside a building, and **18 riderless bodies**.
* **Of 397 people only 14 are at LOD1** and none at LOD0; of 69 vehicles, 5 at LOD1.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the subject is behind a sidewalk shed | the walk snaps to the nearest surveyed sidewalk and tests the view azimuth horizontally; a shed deck four metres up cuts the 56° of elevation the subject needs, and nothing in the clearance test looks up. J87's family, with a sidewalk snap as the specific cause | **verification — open** |
| +5.00 stops, under-lit | the frame is a shaded sidewalk under a deck in February; the number is declared rather than smoothed (J83) | verification — declared |
| mean 1.553×, p50 1.512×, chroma 0.31× | a pale concrete frame against a photograph of dark blue glass, 1.258 stops of development apart | reference + consequence of the row above |
| the top of the subject is cut off | 18 mm is the widest lens the comparison allows and the subject needs 56° at 200 m | **verification — declared limit** |
| 0.336 of mid-field ground under the terrain, min −5.066 m, max +12.091 m | the Hudson Yards platform against a 2013 bare-earth DEM at the platform edge (J85) | geometry — open, measured |
| 2 of 2 structures tiles without a file | no structures file was built for either tile in range | **data — open, two tiles unbuilt** |
| 12,315 kit records in range, 5,735 drawn | the kit triangle budget at 1,338,391 | performance |
| 879 species substituted, 4 scaled out of band, 11 cards dropped | a tree catalogue that does not hold most of the species surveyed here; the props budget was not reached on this sheet | **data — open** |
| 23 props across four kinds unmapped | no asset exists for those kinds | data |
| 729 pedestrians dropped in the carriageway | the walkable surface here is narrower than the street the simulation spawns into | **data — open, measured** |
| the composite reported 2.6° off axis at 348.6 m | the frustum test uses a landmark composite's centroid, 125 m past the member aimed at | verification — open |
| 397 people where the table asked 3,312 | the agent triangle budget plus the placement rules, each with its count | performance + verification |
| four park surface kinds flat-coloured | the texture catalogue has no photographic set for any of them (J40) | **declared decision** |
