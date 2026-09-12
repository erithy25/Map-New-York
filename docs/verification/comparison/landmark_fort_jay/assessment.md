# Fort Jay (Governors Island)

`landmark_fort_jay` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Governors Island - New York City (4889328533).jpg by Doug Kerr from Albany, NY, United States, CC BY-SA 2.0 (https://creativecommons.org/licenses/by-sa/2.0), taken 2010-06-20 14:33, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Governors_Island_-_New_York_City_(4889328533).jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.68841, -74.01672 (NYC_TM -5654, -1315) at z 4.9 m NAVD88 | azimuth 10.4°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1208x906. Position and heading both come from the photograph: its own EXIF camera GPS, **186.9 m** from the item's recorded viewpoint, and 10.4° is the bearing from there to the subject; the item's recorded azimuth of 0.0° is 10.4° away. **The lens stayed at 35 mm and the axis stayed level**, because the highest built thing at the subject's coordinate stands **0.7 m** above the ground there — under the 2 m at which a subject has a height worth aiming or framing by. The recorded viewpoint was **boxed in** — the azimuth closed **40 m** ahead against the 80.0 m needed — so the camera was **moved 32.7 m** onto the nearest surveyed sidewalk, and with no subject height to score against, `scored_on_subject_sightline` is **false**. From there the azimuth is clear for **82.3 m** and the nearest built thing is `t_-6_-2_red_brick` **17.7 m** away. Ground under the camera reads **3.265 m** NAVD88 from 16 heightmap samples within 5.0 m, range 3.2 to 3.4 m.

**Sun** — azimuth 236.5°, elevation 63.6° at 2010-06-20T14:33−04:00, from the photograph's own **EXIF DateTimeOriginal (minutes)**; 926.9 W/m² direct normal, sky at strength 0.0308, Filmic, **+1.11 stops and not clamped**. The linear frame's median is **0.083391** against a middle-grey target of 0.18; the physical rule would have given **0.0 stops** (J83).

**In the scene** — 4,339,777 triangles: 7 building tiles (99,618 tris) with **2 missing**, 3 landmark models of which 1 falls inside the 54.4° frame, 9,710 pavement polygons with **0 dropped**, 2,059 props, 6,391 kit pieces, 19 park-ground meshes over 170 surfaces, 8 structures tiles (**131,492 tris**, 1 without a file), 50 vehicles and 69 people, terrain 105,800 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the fort's earthwork exists in this build as a pad 0.7 metres high, so there was nothing to aim at and the render is a street of parked cars three hundred metres short of the subject

**The fort is not modelled as a fort.** The probe found fabric on all 43 rays and the highest built thing at the subject's coordinate is `lm_b_governors_island.12`, **0.7 m** above the ground there. The reference is a granite scarp four metres tall carrying a grassed earthwork rampart with a cannon on it: the whole subject is a mass of earth and stone, and in this build it is a flat pad. Because 0.7 m is under the 2 m threshold, no height was taken, the axis stayed level, the lens stayed at 35 mm, and **no sightline was tested** — one of the 7 sheets in that state recorded under **J96**.

**So the frame is a street.** A brick barracks block on the left with its window openings, a line of street trees, a sidewalk, a kerb, a wide asphalt roadway, and **five parked cars along it** — on an island that has carried no private traffic for twenty years. This is the second Governors Island sheet to show it: 50 vehicles here, 86 on Castle Williams, and the record carries no `vehicle_on_a_car_free_park_drive` drop on either, because the rule is built only inside a hard-coded Central Park polygon (**J95**).

**What the render does well is the ordinary fabric.** The brick reads correctly with real window openings, the kit was **fully placed** — 6,391 of 6,391 records in range, nothing capped and nothing suppressed — and the canopy is among the best in the pass: **184 of 1,831 trees drawn from modelled branches** and **688 of the 1,647 impostor cards procedural canopy stems**. The structures tiles carry **131,492 triangles**, the highest count in this queue.

**The tonal gap is a cumulus sky.** Contrast **0.547×** and a ninety-fifth percentile of **0.7364** against the photograph's **0.9378**: the reference is half bright cloud over deep green grass, and nothing in this build reads a historical sky. Chroma **0.715×**, median **1.201×**, with the two development offsets **0.566 stops** apart (J83).

## What matches

* **The brick barracks block is right**: real window openings, correct storey height, correct colour for Governors Island's officers' quarters.
* **The kit was fully placed** — 6,391 of 6,391 in range, nothing capped, nothing suppressed.
* **The canopy is among the best in the pass**: 184 trees from modelled branches and 688 procedural canopy stems, with only 3 cards dropped.
* **Structures coverage is the strongest in this queue**: 8 tiles, **131,492 triangles**, 1 without a file.
* **The development is metered and unclamped**, +1.11 stops from a median linear luminance of 0.083391.
* **Ground clearance is excellent**: over all draws the median is **+0.205 m**, the under-fraction **0.0596** and z-fighting **0.0073** — and within 150 m, **0.0** of 334 samples sit under the terrain.
* **The day type is right and was read**: the crowd clock reads **Sunday** for 2010-06-20, which was a Sunday.
* **The record states both of its own limits** — the 0.7 m subject and the fact that the walk was not scored on a sightline — rather than implying a verdict it did not measure.

## What does not match

* **Fort Jay's earthwork and scarp are a 0.7 m pad**, so the subject of this sheet does not exist in the build.
* **No height, no tilt, no sightline verdict** (J96), and the fort is 365.1 m away outside the frame.
* **Fifty private cars on a car-free island** (J95), with no drop recorded.
* **Two of 7 building tiles have no shell file**, and park ground was not built for 2 tiles.
* **Contrast is 0.547 of the photograph's** and the ninety-fifth percentile **0.7364** against **0.9378** — no cumulus, no bright cloud edge.
* **Chroma is 0.715 of the photograph's**, 0.0736 against 0.1029 — the reference's deep summer green against pale mown grass in the render.
* **Forty-four per cent of the props are missing**: 2,059 placed of **3,675 in range**, with **1,590 dropped for the triangle budget** of 1,387,710.
* **1,577 tree rows did not fit** that budget, **1,143** species were substituted and **5** instances were scaled out of band.
* **Sixty-nine people.** The table asked for 281 and 497 were simulated; **151 were dropped for standing where the planimetric data has no sidewalk** and 154 in the carriageway without crossing — on an island whose surface is mostly lawn and path.
* **Seven props across five kinds were wanted in range and have no asset**: 3 artwork, 1 drinking fountain, 1 memorial, 1 swimming pool, 1 vending machine. The fort's own sculpted trophy over the sally port, which the viewpoint note names as the subject, is in the artwork class.
* **Seven park-ground surface kinds fall back to the builder's flat colour** — infield dirt, sport court, greenstreet grass, park grass, pool water, recreation grass, bare ground (J40).
* **The frustum reports the Governors Island composite at 448.3 m, 18.6° off axis**, which is the composite centroid rather than the fort.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the fort is a 0.7 m pad | an earthwork fortification is not a class this build models; the composite carries a flat pad where the rampart and scarp stand | **geometry — open, declared scope, and it removes the subject entirely** |
| no height, no tilt, no sightline | the highest built thing at the coordinate is 0.7 m, under the 2 m framing threshold (J96) | **verification — open, J96** |
| 50 private cars on a car-free island | the car-free rule is built only inside a hard-coded Central Park polygon (J95) | **data — open, J95** |
| 2 of 7 building tiles without a shell, 2 without park ground | no files were built for those tiles; the record names them | **data — open, measured** |
| sd 0.547×, p95 0.7364 against 0.9378 | nothing in this build reads a historical sky, so a half-cumulus reference cannot be matched | reference — no source exists |
| chroma 0.715× | pale mown-grass flat colour against deep summer green (J40) | **declared decision** |
| 2,059 props of 3,675 in range, 1,577 tree rows dropped | the props triangle budget at 1,387,710 | **performance** |
| 1,143 species substituted, 5 scaled out of band | the tree catalogue does not hold most species surveyed here | data |
| 69 people, 151 dropped off the walkable surface | the island's lawns and paths are not walkable surface in the planimetric data | **data — open, measured** |
| 7 props unmapped, the sally-port trophy among them | no asset exists for those kinds | **data — open** |
| seven park surface kinds flat-coloured | the texture catalogue has no photographic set for any of them (J40) | **declared decision** |
| the composite reported 18.6° off axis | the frustum test uses a landmark composite's centroid | verification — open |
