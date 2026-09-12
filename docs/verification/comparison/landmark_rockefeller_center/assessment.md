# Rockefeller Center (30 Rockefeller Plaza)

`landmark_rockefeller_center` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Rockefeller Center British Empire Building Gold-Leaf-Figures 2021-05-13 17-37.jpg by Axel Tschentscher, Public domain (https://commons.wikimedia.org/wiki/Commons:Licensing#Material_in_the_public_domain), taken 2021-05-13 17:37:41, 1920x2909. [Commons page](https://commons.wikimedia.org/wiki/File:Rockefeller_Center_British_Empire_Building_Gold-Leaf-Figures_2021-05-13_17-37.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.75880, -73.97760 (NYC_TM -2331, 6530) at z 23.4 m NAVD88 | azimuth 296.9°, pitch +0.4° | 27 mm on 36 mm (47.3° horizontal, 67.1° vertical, portrait) | 848x1284. The camera stands on **the item's recorded viewpoint**: this photograph's own EXIF GPS is 39 m away and the eye point there is **inside `t_-3_6_roof_membrane`**, while the recorded viewpoint is in open air. The recorded azimuth of 296.9° agrees with the bearing to the subject from the position used to **0.1°**. The lens was **widened from 35 mm to 27 mm** and the axis tilted **+0.4°** to contain the subject: `t_-3_6_roof_membrane`, the built thing standing at the subject's coordinate, tops out 71 m above the lens at 123 m, **30° above the horizon**. **The verticals converge, so this frame is not comparable with the photograph on proportion.** The camera was **not moved** — the view azimuth is clear for **150 m** against the **61.5 m** this frame needs — and the nearest built thing in the frame is `t_-3_6_limestone` **2.6 m** away at 23.7°. Ground under the camera reads **21.758 m** NAVD88, the 10th percentile of **113** heightmap samples within 12 m, range 21.71 to 22.26 m.

**Sun** — azimuth 272.8°, elevation 26.0° at 2021-05-13T17:37:41−04:00, from the photograph's own **EXIF DateTimeOriginal**; 730.5 W/m² direct normal, sky at strength 0.0375, Filmic, **+3.71 stops and not clamped**. The linear frame's median is **0.013742** against a middle-grey target of 0.18 (J83). The physical rule would have given **+0.73 stops**.

**In the scene** — 4,500,150 triangles: 7 building tiles (329,568 tris, none missing, none LOD-substituted), 13 landmark models of which 2 fall inside the 47.3° frame, 27,200 pavement polygons with **0 dropped**, 723 props, 2,253 kit pieces, 27 park-ground meshes over 321 surfaces, 2 structures tiles (2,920 tris), 50 vehicles and 273 people, terrain 85,690 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — these two halves cannot be compared: the photograph is a close-up of gilded bronze door figures, and the render is a street looking up an avenue

**The reference is not a picture of a building.** It is the British Empire Building's gold-leaf panel — eight gilded figures labelled SALT, WHEAT, WOOL, COAL, FISH, COTTON, TOBACCO and SUGAR on a blue-grey bronze door, photographed from a few metres away. Nothing in this build models relief sculpture, gilding or a bronze door, and nothing in this build ever could from a 123 m standoff. **No render of any quality could match this photograph**, so every tonal ratio on this sheet is a coincidence rather than a measurement — including the chroma ratio of **0.965**, which is a gilded door happening to land near a limestone street.

**The chooser's remaining blind spot is scale, and this is where it shows.** I12 records that the chooser establishes no view *direction*; it also establishes no view *scale*. Matching the chosen file's Commons title against the item's declared subject across all 172 records finds **three** items whose subject is an exterior building or place and whose chosen photograph depicts something the build does not model at all: this one (gilded door figures), the Port Authority Bus Terminal (a stair down to the A/C/E platform — an interior, on an item marked `interior: false`), and Domino Park (flowers). Recorded as **J93**.

**The render half has its own fault, and it is not small.** `t_-3_6_limestone` stands **2.6 m from the lens** and fills the right half of the frame as a blank, windowless limestone wall — the nearest occluder measured on any sheet in this pass. The record reports it, states the azimuth clear for 150 m, and certifies the frame, because nothing measures what fills it (J92).

**And the subject was never found.** The probe cast 43 rays and **2** landed on built fabric — the lowest in the pass. The object it measured is `t_-3_6_roof_membrane`, a **tile mesh**: every roof-membrane surface of that whole tile joined into one object, extent **1074.9 m by 1069.5 m**, which the record correctly refuses to use as the subject's extent. The height it reports, **74.27 m**, is a roof membrane somewhere in that tile and not 30 Rockefeller Plaza, whose catalogue entry sits 65.3 m away carrying **259.1 m**. The sightline agrees: 13 rays, **7 clear**, **2 on the subject**, visible fraction **0.154**, the ray blocked at 18.3 m by `prop_tree_honeylocust_medium_70` and the one that gets furthest landing on `prop_lamp_cobra_davit_275` at 103.7 m.

## What matches

* **The development is metered and unclamped**, +3.71 stops from a median linear luminance of 0.013742 against the 0.18 target, where the physical rule would have given +0.73 (J83).
* **The camera correctly refused the photograph's own GPS**, because a ray straight up from that eye point hits a roof, and the recorded viewpoint 39 m away is in open air.
* **The trees are the best in this pass.** 83 of the 136 in range are drawn from their modelled branches rather than as cards, mean scale **0.926**, **0** out of band — and the render's foreground is a plausible line of street honeylocusts over a sidewalk.
* **The crowd reads as a Midtown sidewalk**: 273 people, of whom **40 at LOD1 and 3 at LOD0**, walking on real surveyed sidewalk rather than floating.
* **The pavement is complete**: 27,200 polygons, **0 dropped**, including 11,904 white markings, 5,387 sidewalk, 4,548 roadbed, 3,278 curb, 1,252 plaza and 608 crosswalk.
* **The record is honest about the objects it measured.** It names the tile mesh, says a tile mesh's extent is not the subject's, and refuses to use it — which is why the fault above is legible at all (J74).

## What does not match

* **The two halves are of different things** — gilded relief sculpture against a street view. This is not a fidelity gap in the build; it is a reference-selection fault (J93).
* **2 of 43 height-probe rays found built fabric.** The measured 74.27 m belongs to a roof membrane in tile `t_-3_6`, not to the 259.1 m tower the catalogue names 65.3 m away.
* **Visible fraction 0.154**, 2 of 13 rays, with a honeylocust closing the sightline at 18.3 m and a cobra-head lamp taking the longest ray at 103.7 m (J88).
* **A blank limestone wall 2.6 m from the lens** fills the right half of the frame, unnamed by any frame-content measurement (J92).
* **Rockefeller Plaza's rink is a flat colour.** `park_skating_rink_ice` is one of six park-ground kinds kept at the builder's authored colour because the texture catalogue has no photographic set for rink ice (J40) — on the one sheet in the set where the rink is the place.
* **Five of 7 structures tiles in range have no structures file**, and the 2 that do contribute **2,920 triangles** in total, under the densest subway concourse in Midtown.
* **23,233 kit records were in range and 2,253 were drawn**, capped at a 571,320-triangle budget — the smallest kit budget on any landmark sheet in this pass, and the reason the limestone walls are blank.
* **975 tree rows did not fit** the props budget of 892,157 triangles, **0** of the 53 cards are procedural canopy stems, and 4 impostor cards were dropped.
* **There is no park ground within 400 m to check** — 0 samples near, 0 mid. Beyond 400 m the park surface sits under the terrain on **0.3499** of 543 samples, minimum **−1.907 m**, the worst far-band under-fraction on any landmark sheet here (J85).
* **Eleven props across four kinds were wanted in range and have no asset**: 7 artwork, 2 memorial, 1 drinking fountain, 1 passenger-information sign. On this block, "artwork" is Prometheus and Atlas.
* **The frustum names 30 Rockefeller Plaza 15.9° off axis at 163.3 m** while the subject's own coordinate is 123.0 m away on the axis — the landmark composite's centroid again, 40 m further out than the thing aimed at.
* **The crowd is a seventeenth of the ask.** The density table wanted **1,511 vehicles and 4,713 people**; 1,729 and 2,999 were simulated and **4,402** dropped — 1,360 pedestrians and 530 vehicles at the agent triangle budget, 1,111 pedestrians and 1,102 vehicles outside the radius, 208 pedestrians in the carriageway without crossing, 42 not on a walkable surface, 5 above the observer, and **47 riderless bodies**.
* **A pedestrian stood 4.7 m from the lens and was culled for being over the observer**; the nearest surviving agent is 10.7 m away at −7.9°. The record states both figures, which is right, and the 8 m nothing-built rule still does not apply to the crowd (J91).

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the two halves show different things | the chooser matches a photograph to a *place* and to subject terms in its title, and has no evidence of the photograph's **scale**: a close-up of ornament passes for a picture of the building it is bolted to. 3 of 172 items are affected | **verification — open, J93** |
| 2 of 43 probe rays on built fabric; 74.27 m against a 259.1 m catalogue entry | the object standing at the subject's coordinate is a tile mesh of joined roof membranes, so the probe measured a roof somewhere in the tile; the record says so rather than passing the figure off (J74) | **verification — open, and correctly reported** |
| visible fraction 0.154 | a street tree at 18.3 m and a cobra-head mast on the longest ray; the clearance walk weighs neither (J88) | verification — open |
| a blank wall 2.6 m from the lens filling the right half | the record measures the azimuth and the path to the subject, never the frame's content (J92) | **verification — open, J92** |
| the rink is a flat colour | the texture catalogue has no photographic set for rink ice, and the builder's colour is kept rather than the nearest wrong material (J40) | **declared decision** |
| 5 of 7 structures tiles without a file | no structures file was built for those tiles | **data — open, five tiles unbuilt** |
| 23,233 kit records in range, 2,253 drawn | the kit triangle budget at 571,320 | performance |
| 975 tree rows dropped, 0 canopy stems | the props triangle budget at 892,157 triangles; no mapped woodland polygon in this radius | performance + declared rule |
| 0.3499 of far park ground under the terrain | the terrain grid coarsens to 40 m beyond the near band (J85) | geometry — open, measured |
| 11 props across four kinds unmapped, Prometheus and Atlas among them | no asset exists for those kinds | data |
| 30 Rockefeller Plaza reported 15.9° off axis at 163.3 m | the frustum test uses a landmark composite's centroid | verification — open |
| 273 people where the table asked 4,713 | the agent triangle budget plus the placement rules, each with its count | performance + verification |

## What this sheet is good for

It cannot verify Rockefeller Center. It does two other things. It is the clearest case in the pass of the reference chooser matching on place and subject words while missing scale entirely (J93), and it is the case where the height probe's own honesty is most visible: given a tile mesh 1,075 m across, the record measured what was there, reported 2 of 43 rays, named the object, and refused to use its extent. A chain that reports a bad measurement as a bad measurement is working; the next repair is to refuse the frame, not just describe it.
