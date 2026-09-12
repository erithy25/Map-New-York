# 35 Hudson Yards

`landmark_35_hudson_yards` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Pier 66 and Hudson Yards (01473)p.jpg by Rhododendrites, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2019-08-10 15:28:39, 1920x744. [Commons page](https://commons.wikimedia.org/wiki/File:Pier_66_and_Hudson_Yards_(01473)p.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.75455, -74.00003 (NYC_TM -4302, 6061) at z 7.9 m NAVD88 | azimuth 270.0°, pitch +38.1° | 18 mm on 36 mm (90.0° horizontal, 42° vertical) | 1280x496. The camera stands on **the item's recorded viewpoint**, and the record explains why: this photograph's own EXIF GPS is **947 m** away, past the 250 m at which it could still be the same view, and the record adds that *a fix this far out is usually correct and simply of somewhere else*. The recorded azimuth of 270.0° agrees with the bearing to the subject to **0.0°**. The lens was **widened from 35 mm to the 18 mm floor** and the axis tilted **+38.1°**, and the top of the subject is still cut off: `lm_c_hudson_yards.25` stands 305 m above the lens at 200 m, **57° above the horizon**, against a 42° frame. **The verticals converge, so this frame is not comparable with the photograph on proportion.** The recorded viewpoint was **inside `lm_c_hudson_yards.34`** — a ray straight up from the eye point hits its roof — so the camera was **moved 75.6 m** onto the nearest surveyed crosswalk polygon, scored on the subject's own sightline (11 of 13 rays on the subject at the point chosen). From there the view is clear for **96 m**, the nearest built thing `t_-5_6_park_recreation_grass` **10.1 m** away at 30°. Ground under the camera reads **6.307 m** NAVD88, the 10th percentile of **113** heightmap samples within 12 m, range 6.21 to 10.0 m.

**Sun** — azimuth 242.4°, elevation 49.3° at 2019-08-10T15:28:39−04:00, from the photograph's own **EXIF DateTimeOriginal**; 885.5 W/m² direct normal, sky at strength 0.0321, Filmic, **+6.00 stops, clamped**. The linear frame's median is **0.002319** against a middle-grey target of 0.18, so the meter asked **+6.28 stops** and held at the ceiling. The physical rule would have given **0.0 stops**.

**In the scene** — 4,190,846 triangles: 4 building tiles (189,114 tris, none missing, none LOD-substituted), 7 landmark models of which 3 fall inside the 90.0° frame, 27,934 pavement polygons with **0 dropped**, 895 props, 4,930 kit pieces, 12 park-ground meshes over 125 surfaces, 2 structures tiles (40,632 tris), 89 vehicles and 425 people, terrain 79,930 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the best sightline in this queue, 11 of 13 rays on the subject, spent on a frame that cannot be compared with its photograph: one is a river panorama from 947 m, the other is a kerb looking straight up

**The pairing is the fault, and the record caught it before the render did.** The photograph is a 1920x744 panorama taken from Pier 66 across the Hudson: the whole Hudson Yards cluster in profile over water, with the Frying Pan lightship in the foreground and an August cumulus sky. Its own GPS fix is **947 m** from the item's viewpoint, so the 250 m rule refused to stand the camera on it and used the recorded viewpoint instead — which is a kerb on Tenth Avenue, 123.4 m from the subject, looking straight up at 18 mm and +38.1°. **Two correct decisions compose into an incomparable pair**: the distance rule is right, the recorded viewpoint is right, and no measurement taken between these two halves means anything about tonal match, proportion or skyline.

**What the render does prove is that the sightline machinery works.** The recorded viewpoint was inside a building; the walk moved 75.6 m, scored candidates on how much of the subject each one sees, and landed on a point where **12 of 13 rays are clear and 11 land on the subject** — visible fraction **0.846**, the highest in this queue. The frame shows it: two Hudson Yards towers rise out of the top of the picture, the Vessel's copper lattice sits in the lower left, and street trees fill the right.

**The height is measured, not read, and the record says why.** `lm_c_hudson_yards.25`, **307.4 m** above a ground of 9.48 m, **43 of 43** rays on built fabric, plan extent **42.1 m by 40.6 m**. The nearest catalogue origin is **169.9 m** away — outside the 120 m the old rule looked in — and the record states outright that *this height comes from the geometry and not from the catalogue (J74)*. For a 307 m tower that is the right answer and the catalogue's 387.1 m composite figure would have been the wrong one.

**The exposure is where this frame breaks.** Clamped at +6.00 against 6.28 asked, and the result has a fifth percentile of **0.1003** and a ninety-fifth of **1.0** — the sky is fully blown. Standard deviation **0.3374** against the photograph's **0.17**, a ratio of **1.985**, the widest contrast gap in this queue, and it is clipping rather than range.

## What matches

* **The sightline is the strongest in the queue**: 13 rays, 12 clear, **11 on the subject**, visible fraction **0.846**, with only a honeylocust at 26.1 m taking the other two.
* **The clearance walk worked exactly as designed**: it detected a viewpoint inside a building, moved 75.6 m to real surveyed crosswalk, and ranked the destination on the subject's sightline rather than on eye-level clearance (J79).
* **The height came from the geometry, with the reason recorded.** 307.4 m measured over 43 of 43 rays, against a catalogue origin 169.9 m away that the rule correctly refused to use (J74).
* **The day type is right and was read**: the crowd clock reads **Saturday** for 2019-08-10, which was a Saturday.
* **Near-field ground is perfect**: within 150 m, **0.0** of 374 park-surface samples sit under the terrain, median clearance **+0.215 m**, minimum **+0.003 m**.
* **The Vessel is in the frame and recognisable** — the copper stair lattice in the lower left is the only piece of Hudson Yards ornament this build models, and it reads.
* **The pavement is complete**: 27,934 polygons, **0 dropped**, including 13,999 white markings, 4,887 roadbed, 4,158 sidewalk, 3,356 curb and 665 crosswalk.
* **The crowd is the largest drawn in this queue**: 425 people and 89 vehicles.
* **102 of 330 trees are drawn from modelled branches**, mean scale **0.928**, **0** out of band.

## What does not match

* **The two halves are not the same view.** A 947 m river panorama against a 123 m upward frame: no tonal, proportional or skyline comparison on this sheet is meaningful.
* **The sky is blown.** Ninety-fifth percentile **1.0** against the photograph's 0.7805, and standard deviation **1.985×** — clipping, not contrast.
* **The top of the subject is cut off** at the 18 mm floor and +38.1°; the tower needs 57° of elevation at 200 m against a 42° frame.
* **Chroma is 0.424 of the photograph's**, 0.091 against 0.2145 — the reference carries a blue August sky, cumulus, river water and a red lightship; the render carries glass, asphalt and green canopy.
* **Mid-field ground is the worst band in this queue**: between 150 and 400 m the park surface sits under the terrain on **0.3202** of 684 samples, minimum **−7.694 m**, and the maximum clearance in the same band is **+9.28 m** — a 17-metre spread across the Hudson Yards platform edge (J85).
* **Both structures tiles in range have no structures file** — 2 of 2 — over the rail yard the platform is built on.
* **7,719 kit records were in range and 4,930 were drawn** — not for the triangle budget, which was never reached here, but because 2,789 were suppressed where a landmark supplies its own shell.
* **1,411 tree rows did not fit** the props budget of 1,229,582 triangles, **0** of the 228 impostor cards are procedural canopy stems, 4 cards were dropped, and **287 of 330** tree species were substituted.
* **Twenty-two props across eight kinds were wanted in range and have no asset**: 10 misc structure, 5 drinking fountain, 2 artwork, 1 billboard, 1 parks building, 1 parks comfort station, 1 passenger-information sign, 1 vending machine.
* **Every vehicle is at LOD2** — 89 of 89 — and of 425 people only 4 are at LOD1.
* **Four park-ground surface kinds fall back to the builder's flat colour** — sport court, park grass, recreation grass, bare ground (J40).
* **The frustum names the Hudson Yards composite 56.1° off axis at 84.4 m** while the subject is 123.4 m away on the axis: the composite's centroid again.
* **The crowd is an eighth of the ask**: the table wanted 850 vehicles and 3,712 people; 1,027 and 2,999 were simulated and **3,511** dropped — 1,267 pedestrians and 518 vehicles outside the radius, 531 pedestrians and 373 vehicles at the agent triangle budget, **480 pedestrians in the carriageway without crossing**, 288 not on a walkable surface, 13 vehicles not on a carriageway, 7 inside a building, and **34 riderless bodies**.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the two halves are not the same view | the photograph's own fix is 947 m from the item's viewpoint, so the 250 m rule used the recorded viewpoint; both decisions are correct and the pairing is still incomparable. The chooser has no rule that a panorama of a cluster cannot serve an item whose viewpoint is a kerb inside it — J93's family in the distance dimension | **verification — open** |
| the sky is blown, p95 1.0, sd 1.985× | +6.00 stops clamped against 6.28 asked, applied to a frame that already contained direct sky at 49° sun elevation | verification — declared clamp |
| the top of the subject is cut off | 18 mm is the widest lens the comparison allows and the subject needs 57° at 200 m | **verification — declared limit** |
| chroma 0.424× | no sky, no water and no painted hull in the render's frame | consequence of the pairing |
| 0.3202 of mid-field ground under the terrain, min −7.694 m, max +9.28 m | the Hudson Yards platform against a 2013 bare-earth DEM, at the platform edge where the two disagree most (J85) | geometry — open, measured |
| 2 of 2 structures tiles without a file | no structures file was built for either tile in range | **data — open, two tiles unbuilt** |
| 7,719 kit records in range, 4,930 drawn | 2,789 suppressed where a landmark shell stands in place of the tile's buildings; the kit budget was not reached | **declared rule** |
| 1,411 tree rows dropped, 287 species substituted, 0 canopy stems | the props triangle budget at 1,229,582 triangles, and a tree catalogue that does not hold most surveyed species here | performance + **data** |
| 22 props across eight kinds unmapped | no asset exists for those kinds | data |
| 89 of 89 vehicles at LOD2 | the LOD rule picks by distance and the traffic in range sits beyond the nearer bands | performance |
| the composite reported 56.1° off axis | the frustum test uses a landmark composite's centroid | verification — open |
| 425 people where the table asked 3,712 | the agent triangle budget plus the placement rules, each with its count | performance + verification |
| four park surface kinds flat-coloured | the texture catalogue has no photographic set for any of them (J40) | **declared decision** |
