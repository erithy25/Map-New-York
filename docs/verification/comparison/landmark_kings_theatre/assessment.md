# Kings Theatre (Flatbush)

`landmark_kings_theatre` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Kings Theatre Exterior 01.jpg by Alexandra Silversmith, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2015-10-18 13:45:32, 1920x2560. [Commons page](https://commons.wikimedia.org/wiki/File:Kings_Theatre_Exterior_01.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.64601, -73.95806 (NYC_TM -693, -5995) at z 11.1 m NAVD88 | azimuth 89.2°, pitch +6.5° | 35 mm on 36 mm (42.2° horizontal, 54.4° vertical, portrait) | 904x1206. Position and heading both come from the photograph: its own EXIF camera GPS, **13.4 m** from the item's recorded viewpoint — the closest agreement in this queue — and 89.2° is the bearing from there to the subject, **1.7°** from the item's own azimuth. The recorded viewpoint was **boxed in** — the azimuth closed **10 m** ahead against the 34.4 m needed — so the camera was **moved 10.1 m** onto the nearest surveyed sidewalk, scored on the subject's sightline, which returned 2 of 13 rays at the point chosen and was still the best available. From there the azimuth is clear for **37.4 m** and the nearest built thing is `prop_lamp_cobra_davit_1` **12.0 m** away. Ground under the camera reads **9.55 m** NAVD88, the 10th percentile of **113** heightmap samples within 12 m, range 8.3 to 11.18 m.

**Sun** — azimuth 200.2°, elevation 37.5° at 2015-10-18T13:45:32−04:00, from the photograph's own **EXIF DateTimeOriginal**; 826.7 W/m² direct normal, sky at strength 0.0340, Filmic, **+1.97 stops and not clamped**. The linear frame's median is **0.045893** against a middle-grey target of 0.18; the physical rule would have given **+0.20 stops** (J83).

**In the scene** — 3,540,080 triangles: 4 building tiles (363,952 tris, none missing, none LOD-substituted), 1 landmark model, in the frame at **1.1° off axis**, 14,347 pavement polygons with **0 dropped**, 1,108 props, 4,463 kit pieces, 11 park-ground meshes over 114 surfaces, 3 structures tiles (2,228 tris) with 1 without a file, 85 vehicles and 297 people, terrain 80,000 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the theatre's brick flank is modelled and its terracotta front is not, and a street lamp twelve metres from the lens takes eleven of the thirteen rays

**The reference is the front.** A close-up looking up at the 1929 terracotta parapet — cartouches, a masked keystone, a coat of arms, urns at the corners — over the marquee with KINGS THEATRE in gilt letters and the evening's booking on the board below. It is entirely ornament and lettering.

**The render is the side.** A large red-brick mass with a green-banded storefront base, a service door, a rooftop unit, a lamp post, a broad pale sidewalk and a handful of pedestrians. The brick flank, its parapet line and the shopfront band are all right for Flatbush Avenue; nothing of the terracotta front is in the model, and no marquee exists as a class.

**A cobra-head mast takes the frame.** 13 rays, **2 clear, 2 on the subject**, eleven stopped at **13.5 m** by `prop_lamp_cobra_davit_1` — visible fraction **0.154**. The walk moved 10.1 m and scored this as the best point it could reach, because the recorded viewpoint was closed off at 10 m. J88 again: the clearance walk clears built fabric along the azimuth and never weighs a street lamp.

**The measurement of the subject is sound.** The probe found **21.84 m** above a ground of 9.52 m over **43 of 43** rays, with a plan extent of **89.2 m by 73.5 m** — the theatre's real footprint — against a catalogue entry standing **0.0 m** away, exactly on the coordinate, carrying 25.2 m. The 3.4 m difference is the parapet the rays struck against the crown the entry records.

**And the kit is one of the better sets in the pass**: 4,463 pieces placed of 4,909 in range, nothing capped, 446 suppressed under the landmark shell — including **402 storefronts, 135 parapets, 126 door entries, 108 fire escapes, 85 cornices and 85 quoins**. Flatbush Avenue's shopfronts and cornices are drawn, and it shows.

**Chroma is the cost of the missing front**: **0.0706** against **0.2203**, a ratio of **0.32**. The reference's gilt, polychrome terracotta and deep blue sky are the saturated content, and the render's frame is brick, concrete and a pale sky.

## What matches

* **The camera stands 13.4 m from the item's own viewpoint** with a bearing 1.7° from its recorded azimuth — the closest pairing in this queue.
* **The brick flank, its parapet and the storefront band** are all right in scale, colour and storey height.
* **The kit is nearly complete**: 4,463 of 4,909 in range, nothing capped, with 402 storefronts and 135 parapets among them.
* **Props were not capped and nothing was unmapped** — 1,108 placed of 1,230 in range, **0** unmapped kinds.
* **The probe is complete and the extent is the real footprint**: 43 of 43 rays, 89.2 m by 73.5 m (J74).
* **The landmark is in the frame at 1.1° off axis** — the frustum test agrees with the picture.
* **The development is metered and unclamped**, +1.97 stops from a median linear luminance of 0.045893.
* **The day type is right and was read**: the crowd clock reads **Sunday** for 2015-10-18, which was a Sunday.
* **Ground clearance is good**: over all draws the median is **+0.185 m**, the under-fraction **0.1011** and z-fighting **0.0122**.

## What does not match

* **The terracotta front, the marquee and the gilt lettering are absent** — the whole subject of the reference.
* **Visible fraction 0.154**, eleven of thirteen rays stopped by a street lamp 13.5 m from the lens (J88).
* **Chroma is 0.32 of the photograph's**, 0.0706 against 0.2203.
* **The median is 1.32× the photograph's**, most of it the 0.853-stop difference between the two developments (J83).
* **No cloud.** The reference's October sky carries bright cumulus; the render's is a Nishita dome at strength 0.0340.
* **Only 23 of 684 trees are drawn from modelled branches**; **245** species were substituted, **1** instance scaled out of band, 7 cards dropped, and **0** of the 661 cards are procedural canopy stems.
* **One of 3 structures tiles has no structures file**, and the 3 imported carry **2,228 triangles** in total.
* **Park ground was not built for 2 tiles**, and there is no park ground within 150 m to check — 0 samples.
* **Seven park-ground surface kinds fall back to the builder's flat colour** (J40).
* **The crowd is a quarter of the ask**: the table wanted 308 vehicles and 1,246 people; 370 and 1,605 were simulated and **1,588** dropped — 587 pedestrians and 194 vehicles outside the radius, **543** pedestrians and 78 vehicles at the agent triangle budget, 130 pedestrians in the carriageway without crossing, 43 with no sidewalk under them, 5 above the observer, and **13 riderless bodies**.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no terracotta front, marquee or lettering | the landmark builder models massing and the facade kit places generic pieces; polychrome terracotta ornament and a theatre marquee are not classes this build authors, and no sign copy is invented anywhere (DEVIATIONS B15a) | geometry — declared scope + **declared decision** |
| visible fraction 0.154 | a cobra-head mast 13.5 m from the lens takes eleven of thirteen rays; the walk weighs built fabric and never weighs a street lamp (J88) | **verification — open, J88** |
| chroma 0.32× | the saturated content of the reference is gilt and polychrome terracotta, none of which exists in the model | consequence of the row above |
| p50 1.32× | 0.853 stops of development between the halves (J83) | reference |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
| 23 of 684 trees from modelled branches, 245 species substituted | the props budget spends its triangles on cards at this density, and the tree catalogue does not hold most species surveyed here | performance + **data** |
| 1 of 3 structures tiles without a file, 2,228 triangles from the rest | no structures file was built for that tile, and Flatbush has little elevated structure to carry | data — open |
| park ground missing on 2 tiles | not built for those tiles; the record names both | **data — open, two tiles unbuilt** |
| seven park surface kinds flat-coloured | the texture catalogue has no photographic set for any of them (J40) | **declared decision** |
| 297 people where the table asked 1,246 | the agent triangle budget plus the placement rules, each with its count | performance + verification |
