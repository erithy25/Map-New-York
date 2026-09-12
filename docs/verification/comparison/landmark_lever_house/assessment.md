# Lever House (390 Park Avenue)

`landmark_lever_house` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Park Av 53 St Mar 2021 47.jpg by Epicgenius, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2021-03-21 12:54:19, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Park_Av_53_St_Mar_2021_47.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.75864, -73.97313 (NYC_TM -1948, 6481) at z 18.3 m NAVD88 | azimuth 13.9°, pitch +4.2° | 18 mm on 36 mm (90.0° horizontal, 74° vertical) | 1208x906. Position and heading both come from the photograph: its own EXIF camera GPS, **107.4 m** from the item's recorded viewpoint, and 13.9° is the bearing from there to the subject. The item's recorded azimuth of 70.0° is **56.1° away**. The lens was **widened from 35 mm to the 18 mm floor** and the axis tilted **+4.2°**, and the top of the subject is still cut off: `lm_c_lever_house.2` stands 92 m above the lens at 124 m, **37° above the horizon**. **The verticals converge, so this frame is not comparable with the photograph on proportion.** The recorded viewpoint was **boxed in** — the azimuth closed **21 m** ahead against the 61.8 m needed — so the camera was **moved 30.8 m** onto the nearest surveyed crosswalk, scored on the subject's sightline, which returned 1 of 13 rays at the point chosen and was still the best available. From there the azimuth is clear for **74.2 m**, nothing built stands within 20 m of the lens, and **a simulated black car stands 7.8 m away**. Ground under the camera reads **16.655 m** NAVD88, the 10th percentile of **113** heightmap samples within 12 m, range 16.51 to 17.51 m.

**Sun** — azimuth 176.7°, elevation 49.7° at 2021-03-21T12:54:19−04:00, from the photograph's own **EXIF DateTimeOriginal**; 886.9 W/m² direct normal, sky at strength 0.0320, Filmic, **+2.79 stops and not clamped**. The linear frame's median is **0.026026** against a middle-grey target of 0.18; the physical rule would have given **0.0 stops** (J83).

**In the scene** — 4,500,113 triangles: 6 building tiles (309,456 tris, none missing, none LOD-substituted), 13 landmark models of which 5 fall inside the 90.0° frame, 29,311 pavement polygons with **0 dropped**, 850 props, 4,314 kit pieces, 23 park-ground meshes over 295 surfaces, 2 structures tiles (2,920 tris) with **4 without a file**, 53 vehicles and 250 people, terrain 86,802 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the green curtain wall that is the whole point of Lever House is behind a street lamp twenty-seven metres from the lens, and the kit budget on this sheet is the smallest in Midtown: 4,314 pieces drawn of 61,493 in range

**Visible fraction 0.077.** Thirteen rays, **5 clear, 1 on the subject**, blocked at **27.2 m** by `prop_lamp_cobra_davit_1`. The reference is Lever House seen across Park Avenue: a blue-green glass slab on a raised podium over an open colonnade, the curtain wall's mullion grid reading clearly. The render looks up the same avenue and shows a brown-brick block on the left, a receding canyon, a crossing crowd — and no green glass.

**The measurement of the subject is nonetheless exact.** The probe found **94.62 m** above a ground of 15.54 m over **43 of 43** rays, and the catalogue entry 14.5 m away carries **94.0 m** — agreement within two thirds of a metre. The plan extent measured off the object is **50.1 m by 35.6 m**, which is the tower slab's footprint.

**The kit budget here is the tightest on any Midtown sheet in the pass.** **61,493** records in range, **4,314** drawn, capped at **710,773 triangles** — a budget barely more than half what most sheets get — with 132 more suppressed. On Park Avenue at 54th Street, that is why the avenue's walls carry a window grid and nothing else: no spandrel, no reveal, no cornice, and on the subject itself no curtain wall at all.

**The crowd is the best thing in the picture.** 250 people drawn, grouped at the crossing with their own shadows, at mixed levels of detail. It is also where the 8 m rule fails again: a black car stands **7.8 m** from the lens (J91).

**The tonal pairing is close.** Mean **1.151×**, median **1.23×**, chroma **0.824×**, with the two development offsets **0.638 stops** apart.

## What matches

* **The probe and the catalogue agree within two thirds of a metre** — 94.62 m against 94.0 m (J74).
* **The clearance walk worked as designed**: a 21 m closure detected, 30.8 m onto a real surveyed crosswalk, scored on the subject's sightline (J79).
* **The crowd reads as Midtown at lunchtime**: 250 people at the crossing with shadows, 9 vehicles at LOD1.
* **Five landmark models fall inside the 90° frame** — the Seagram Building at 78.6 m, Lever House at 139.4 m, the Plaza at 688.5 m, Billionaires' Row at 707.8 m and the Central Park wall at 2,915.4 m — and the frustum's **−6.3°** for Lever House agrees with the picture.
* **The development is metered and unclamped**, +2.79 stops from a median linear luminance of 0.026026.
* **The pavement is complete**: 29,311 polygons, **0 dropped**, including 13,669 white markings, 5,119 sidewalk, 4,508 roadbed, 3,614 curb, 1,082 plaza and 795 crosswalk.
* **64 of 175 trees are drawn from modelled branches**, with bare canopies correct for 21 March.

## What does not match

* **The green curtain wall is not in the frame.** Visible fraction **0.077**, twelve of thirteen rays stopped by a street lamp at 27.2 m (J88).
* **4,314 kit pieces of 61,493 in range**, capped at **710,773** triangles — the tightest kit budget on a Midtown sheet in this pass — with 132 suppressed.
* **The top of the subject is cut off** at the 18 mm floor; it needs 37° of elevation at 124 m.
* **Seventy-seven per cent of the props are missing**: 850 placed of **3,623 in range**, with **2,475 dropped for the triangle budget** of 965,129, 12 on a suppressed building and 6 cards dropped.
* **1,513 tree rows did not fit** that budget, and **0** of the 111 cards are procedural canopy stems.
* **A black car stands 7.8 m from the lens** (J91).
* **Four of 6 structures tiles have no structures file**, and the 2 that do carry **2,920 triangles** — under the Lexington Avenue line.
* **There is no park ground within 150 m to check** — 0 samples. Between 150 and 400 m the under-fraction is **0.25** over 44 samples (J85).
* **Sixteen props across six kinds were wanted in range and have no asset**: 7 artwork, 3 payphone, 2 drinking fountain, 2 memorial, 1 passenger-information sign, 1 vending machine.
* **Six park-ground surface kinds fall back to the builder's flat colour** (J40).
* **The crowd is a seventeenth of the ask**: the table wanted 905 vehicles and 4,549 people; 1,081 and 3,000 were simulated and **3,774** dropped — **1,440** people and 461 vehicles at the agent triangle budget, 217 pedestrians in the roadway while not crossing, 31 with no sidewalk under them, and **24 riderless bodies**.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the curtain wall is not in the frame | a cobra-head mast 27.2 m from the lens closes twelve of thirteen rays; the walk weighs built fabric and never weighs a street lamp (J88) | **verification — open, J88** |
| 4,314 kit pieces of 61,493 in range | the kit triangle budget at 710,773, the tightest on a Midtown sheet here, plus 132 suppressed | **performance — measured** |
| the top of the subject is cut off | 18 mm is the widest lens the comparison allows and the subject needs 37° at 124 m | **verification — declared limit** |
| 850 props of 3,623 in range, 1,513 tree rows dropped | the props triangle budget at 965,129, which dropped 2,475 | **performance** |
| a car 7.8 m from the lens | the 8 m nothing-built rule applies to geometry and not to the crowd (J91) | verification — open |
| 4 of 6 structures tiles without a file | no structures file was built for those tiles | **data — open, four tiles unbuilt** |
| 0.25 of mid-field park ground under the terrain | the terrain grid coarsens to 40 m beyond the near band (J85) | geometry — open, measured |
| 16 props across six kinds unmapped | no asset exists for those kinds | data |
| six park surface kinds flat-coloured | the texture catalogue has no photographic set for any of them (J40) | **declared decision** |
| 250 people where the table asked 4,549 | the agent triangle budget plus the placement rules, each with its count | performance + verification |
