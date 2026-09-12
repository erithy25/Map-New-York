# Belvedere Castle

`landmark_belvedere_castle` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Belvedere Castle and Turtle Pond, Central Park, Manhattan, New York.jpg by Christian David, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2026-04-18 09:53:19, 1920x1080. [Commons page](https://commons.wikimedia.org/wiki/File:Belvedere_Castle_and_Turtle_Pond,_Central_Park,_Manhattan,_New_York.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.77987, -73.96763 (NYC_TM -1488, 8869) at z 32.6 m NAVD88 | azimuth 249.0°, pitch +5.9° | 35 mm on 36 mm (54.4° horizontal) | 1280x720. Position and heading both come from the photograph: its own EXIF camera GPS, **121.6 m** from the item's recorded viewpoint, and 249.0° is the bearing from there to the subject. The item's recorded azimuth of 300.0° is **51.0° away**. The lens stayed at 35 mm and the axis was tilted **+5.9°** to the subject's mid-height, because the object standing at the subject's coordinate measures only 8 m. The camera was not moved — the eye point stands on `t_-2_8_park_park_ground_grass`, and since this position is the photograph's own fix there is no nominal viewpoint to walk to. The azimuth is clear for **113.7 m** against the 64.8 m needed, and the nearest built thing is that same grass surface **6.2 m** away at 27.2° yaw and −16.1° pitch. Ground under the camera reads **31.031 m** NAVD88 from 16 heightmap samples within 5.0 m, range 30.74 to 31.3 m — no surface is named in the viewpoint note, so the heightmap median within 5 m is used.

**Sun** — azimuth 113.6°, elevation 40.2° at 2026-04-18T09:53:19−04:00, from the photograph's own **EXIF DateTimeOriginal**; 842.8 W/m² direct normal, sky at strength 0.0335, Filmic, **+1.23 stops and not clamped**. The linear frame's median is **0.076641** against a middle-grey target of 0.18 (J83). The physical rule would have given **+0.10 stops**.

**In the scene** — 2,377,373 triangles: 6 building tiles (478,980 tris, none missing, none LOD-substituted), 6 landmark models of which 2 fall inside the 54.4° frame, 10,049 pavement polygons with **0 dropped**, 5,578 props, **164** kit pieces, 22 park-ground meshes over 601 surfaces with **2,897 faces cut** for landmark ground, 3 structures tiles (3,720 tris), 18 vehicles and 11 people, terrain 87,808 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the best composition in this queue and the castle stands on a grass mound: Vista Rock, which is half the photograph, does not exist in this build

**The framing and the setting are right.** Turtle Pond fills the foreground as a reflective sheet, a wooded rise carries the middle distance, and a pale crenellated mass with two round towers sits on top of it. The camera stands where the photographer stood, at the bearing to the subject, and the development is metered and unclamped at +1.23 stops. Of everything in this queue this is the frame that most looks like the same place as its photograph.

**Then the two halves part company on the rock.** The photograph's lower half is **Manhattan schist**: a bare grey outcrop, bedded and fractured, dropping straight into the water, with the castle's masonry continuing the same stone upward so that building and rock read as one thing. The render has a **smooth green grass mound** in its place. Nothing in this build models exposed bedrock; the park-ground surface simply continues over it, and the castle's whole reason for standing where it does is gone.

**The castle is massing without masonry.** 164 kit pieces are in range on this sheet — the smallest kit count in the pass — of which 99 are windows and 54 parapets, so the walls carry almost nothing. The photograph's conical slate tower roof reads in the render as a plain cylinder with a domed cap; the open timber pavilion beside it is absent; the stone is one flat pale colour where the reference is grey schist with courses and shadow.

**And the probe measured a terrace, not the castle.** **8.42 m** above a ground of 41.85 m, **43 of 43** rays, on `lm_b_belvedere_castle.2`, against a catalogue entry **4.7 m away** carrying **23.75 m** — one of the 16 records in the J94 survey whose probe height falls below three quarters of a catalogue entry standing within 20 m. Because 8.42 m is under the 12 m floor the fan fell back to the floor and aimed at **3.8 m above that terrace**, returning **13 of 13 rays clear, 12 on the subject**, visible fraction **0.923**. The rays do land on the castle's own fabric; the aim is at its base.

**The tonal comparison is the closest in this queue.** Chroma **0.1203** against **0.1785** (**0.674×**) and mean **1.018×** — spring foliage in both halves, and the render's canopy is carrying it. Contrast is where it falls apart: standard deviation **0.612×** and a fifth percentile of **0.234** against the photograph's **0.1098**, because the render has no dark rock, no shaded masonry and no deep water.

## What matches

* **The composition, the distance and the setting** — pond, rise, castle on top, in that order, at the right bearing.
* **The canopy is the best-founded in the pass**: 5,343 trees placed, of which **3,713 of the 5,332 impostor cards are procedural canopy stems** placed by rule inside mapped woodland polygons. This is exactly what J86's repair was for, and the Ramble reads as woodland rather than bare terrain.
* **The development is metered and unclamped**, +1.23 stops from a median linear luminance of 0.076641, where the physical rule would have given +0.10.
* **Chroma at 0.674× is the closest in this queue**, and the mean is within **1.018×**.
* **The height probe is complete on the object it found** — 43 of 43 rays — and reports the 8.42 m it measured rather than substituting the catalogue's 23.75 m (J74).
* **Near-field ground is sound**: within 150 m, **0.009** of 557 park-surface samples sit under the terrain, median **+0.123 m**.
* **The landmark-ground rule did real work**: **2,897** park-ground faces cut where the castle supplies its own ground.
* **The record is honest about why the traffic is thin**: 21 vehicles were dropped because *the road graph put them on Central Park's East, West, Terrace or Center Drive, which have carried no private traffic since 2018*. That is a rule about the real city, stated in the record, and it is the right rule.
* **Props were not capped**: 5,578 placed of 5,609 in range.
* **The day type is right and was read**: the crowd clock reads **Saturday** for 2026-04-18, which was a Saturday.

## What does not match

* **Vista Rock is not modelled.** The schist outcrop that is half the photograph renders as a grass mound; exposed bedrock is not a class this build carries, and the park-ground surface runs over it.
* **The castle is massing without masonry.** 164 kit pieces in range, the smallest count in the pass; the walls are one flat pale colour.
* **The tower roof is a domed cylinder** where the photograph has a conical slate spire, and **the timber pavilion is absent**.
* **The probe measured 8.42 m for a 23.75 m subject** whose catalogue entry sits 4.7 m away, and the frame was aimed 3.8 m above that member (J94).
* **Contrast is 0.612 of the photograph's** and the fifth percentile is **0.234** against **0.1098** — no dark rock, no shaded stone, no deep water.
* **The pond is a flat mirror.** It reflects the bank cleanly and carries none of the reference's surface texture or depth colour.
* **Eleven people and 18 vehicles.** The table asked for 44 people and 112 vehicles; 56 and 154 were simulated. On a Saturday morning the terrace in the reference has visitors on it and the render's has none.
* **Only 11 of 5,343 trees are drawn from modelled branches**; **1,062** species were substituted, **11** instances were scaled out of band, and 3 cards were dropped.
* **All 3 structures tiles in range have no structures file**, and they contribute 3,720 triangles between the tiles that do exist elsewhere in the scene.
* **Beyond 400 m the park surface sits under the terrain on 0.2479 of 952 samples**, minimum **−3.978 m**, after a redrape that moved **545,423** vertices — the largest redrape in this queue (J85).
* **Twenty-three props across five kinds were wanted in range and have no asset**: 9 drinking fountain, 6 parks building, 5 artwork, 2 parks comfort station, 1 memorial. In Central Park those are the rustic shelters, the fountains and the statuary.
* **Five park-ground surface kinds fall back to the builder's flat colour** — infield dirt, sport court, park grass, recreation grass, bare ground (J40) — and the grass over Vista Rock is one of them.
* **Seventeen pedestrians were dropped for standing where the planimetric data has no sidewalk**, which in the Ramble is most of where people walk.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| Vista Rock renders as a grass mound | exposed bedrock is not a surface class this build models; the open-space survey gives a park-ground polygon and the builder fills it with grass | **geometry — open, declared scope** |
| the castle is massing without masonry | 164 kit pieces in range is all the facade classifier found for a landmark shell, and there is no per-building facade colour or stone coursing (J66 remainder) | geometry — declared scope + **data, open** |
| a domed cylinder for a conical spire, no pavilion | the landmark builder models massing; roof form beyond a cap and small ancillary structures are not authored | geometry — declared scope |
| probe 8.42 m against a 23.75 m catalogue entry 4.7 m away; aim at 3.8 m | the probe takes the object standing at the subject's coordinate, here a terrace, and the fan falls back to the 12 m floor below that (J94) | **verification — open, J94** |
| sd 0.612×, p05 0.234 against 0.1098 | no dark rock, no shaded masonry, no deep water in the render's frame | consequence of the rows above |
| the pond is a flat mirror | water is a flattened surface at a single elevation with no wave or depth model | **declared scope** |
| 11 people, 18 vehicles | the table's own figures are small here and the placement rules drop 17 pedestrians off-sidewalk and 21 vehicles onto car-free park drives — the last of which is correct | verification + **declared rule** |
| 11 of 5,343 trees from modelled branches, 1,062 species substituted | the props budget spends its triangles on cards at this density, and the tree catalogue does not hold most species surveyed in the Ramble | performance + **data** |
| 3 of 3 structures tiles without a file | no structures file was built for any tile in range | **data — open, three tiles unbuilt** |
| 0.2479 of far park ground under the terrain, min −3.978 m | the terrain grid coarsens to 40 m beyond the near band over Central Park's rolling survey shape (J85) | geometry — open, measured |
| 23 props across five kinds unmapped | no asset exists for those kinds | data |
| five park surface kinds flat-coloured | the texture catalogue has no photographic set for any of them (J40) | **declared decision** |
