# Domino Park

`landmark_domino_park` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Domino Park Flowers.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-06-28 13:44:56, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Domino_Park_Flowers.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.71404, -73.96970 (NYC_TM -1664, 1559) at z 1.6 m NAVD88 | azimuth 56.6°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1208x906. Position and heading both come from the photograph: its own EXIF camera GPS, **176.8 m** from the item's recorded viewpoint, and 56.6° is the bearing from there to the subject. The item's recorded azimuth of 120.0° is **63.4° away**. The lens stayed at 35 mm and the axis level, because the highest built thing at the subject's coordinate is 0.3 m tall. The camera was not moved — **nothing built stands within 60 m of the lens**, no agent either, and the azimuth is clear for **150 m** against the 80.0 m needed. **Ground under the camera reads 0.0 m NAVD88, from 16 heightmap samples within 5.0 m whose range is 0.0 to 0.0 m** — a flat water surface. The viewpoint note names the esplanade the photographer stood on, and the record's own rule then uses the heightmap height at that point, which here is the river.

**Sun** — azimuth 212.3°, elevation 70.1° at 2022-06-28T13:44:56−04:00, from the photograph's own **EXIF DateTimeOriginal**; 938.4 W/m² direct normal, sky at strength 0.0305, Filmic, **+1.71 stops and not clamped**. The linear frame's median is **0.055173** against a middle-grey target of 0.18; the physical rule would have given **0.0 stops** (J83). At 70.1° this is the highest sun elevation in the pass.

**In the scene** — 4,231,525 triangles: 9 building tiles (278,754 tris, none missing, none LOD-substituted), 2 landmark models of which 1 falls inside the 54.4° frame, 16,664 pavement polygons with **0 dropped**, 971 props, 8,025 kit pieces, 36 park-ground meshes over 410 surfaces, 9 structures tiles with **none missing** (60,480 tris), 89 vehicles and 206 people, terrain 93,972 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the camera stands on the river at exactly 0.0 m, the park itself has no height worth framing, and the reference is a photograph of coneflowers

**Three separate things go wrong and each one is recorded.** The reference is `File:Domino Park Flowers.jpg`: pink coneflowers and grasses photographed from a metre away in a planting bed. It is one of the three items the title sweep behind **J93** catches — the chooser matched the park's name and has no evidence of whether a photograph shows a place or a plant in it.

**The subject has no height.** The probe found fabric on 5 of 43 rays and the highest built thing at the coordinate is `t_-2_1_park_recreation_grass` standing **0.3 m** above the ground there, which the record calls *below the 2 m at which a subject has a height worth aiming or framing by*. So the axis stayed level, the lens stayed at 35 mm, and **no sightline was tested** — one of the 7 records in that state beside the 13 with no fabric at all (**J96**).

**And the camera is standing on the water.** Ground under the lens reads **0.0 m NAVD88** over 16 samples whose range is **0.0 to 0.0 m**: the flattened river surface. Domino Park's esplanade is a built deck two to three metres above that, and the heightmap carries none of it, so the eye point sits 1.6 m over the river rather than on the walkway the item names. That is why the bottom three fifths of the render is a flat sheet of water, and it is the same class of fault as the Hudson Yards platform recorded in J85 — a built deck that the 2013 bare-earth terrain does not know about — appearing here on a smaller deck and putting the camera in the wrong place rather than the road.

**What the render does get right is the refinery.** The Domino Sugar Refinery's brick mass stands on the right with its tall arched window bays reading correctly, a tan residential tower beside it and the grey slabs of the newer blocks behind. For a facade built from a kit that is a good result: **8,025 kit pieces of 9,058 in range**, nothing capped, 1,033 suppressed under the landmark shell.

**The tonal figures are ordinary.** Mean **0.853×**, median **0.91×**, chroma **0.641×**, contrast **0.743×**, with the two development offsets **0.295 stops** apart (J83). A close-up of flowers against a river view is not a comparison, and these numbers are not evidence about the build.

## What matches

* **The refinery's brick and its arched bays read correctly** at 182 m, and the kit was not capped.
* **Every structures tile in range has a file** — 9 of 9, **60,480 triangles**.
* **The development is metered and unclamped**, +1.71 stops from a median linear luminance of 0.055173, at the highest sun elevation in the pass.
* **The clearance is genuinely clear**: nothing built within 60 m of the lens and no agent either — the 8 m rule satisfied on both counts with room to spare.
* **Near-field ground is perfect**: within 150 m, **0.0** of 165 park-surface samples sit under the terrain, median **+0.20 m**.
* **The record states all three faults plainly** — the 0.3 m subject, the 0.0 m ground with its 0.0-to-0.0 sample range, and the note that the viewpoint's own raised surface is not what the heightmap carries.
* **The pavement is complete**: 16,664 polygons, **0 dropped**, including **10,278** white markings, 2,179 curb, 1,272 sidewalk, 1,174 roadbed and 544 crosswalk.

## What does not match

* **The reference is a photograph of coneflowers** (J93).
* **The camera stands on the river at 0.0 m** instead of on the esplanade, so the frame is three fifths water.
* **The subject has no height worth framing by** — 0.3 m — so there is no tilt, no widened lens and no sightline verdict (J96).
* **The water is a flat mirror.** It reflects the buildings cleanly and carries no wave, current or depth colour, on a tidal strait.
* **The park is not identifiable.** The elevated walkway the viewpoint note names, its planting beds, the syrup tanks and the crane track are all absent; what stands on the shoreline is a low pale edge.
* **Fifty-seven per cent of the props are missing**: 971 placed of **2,286 in range**, with **1,202 dropped for the triangle budget** of 1,221,034.
* **Not one of 158 trees is drawn from modelled branches**; **1,108 tree rows** did not fit the props budget, **0** of the cards are procedural canopy stems, **66** species were substituted and the mean scale of **0.835** undersizes the canopy.
* **Park ground was not built for 3 tiles** inside the 888 m ground radius, so those render as bare terrain.
* **Beyond 400 m the park surface sits under the terrain on 0.1945 of 1,964 samples**, minimum **−3.979 m**, with a z-fighting fraction of **0.0494** (J85).
* **Nine park-ground surface kinds fall back to the builder's flat colour** — infield dirt, sport court, grass field, greenstreet grass, park grass, pool water, recreation grass, running track, bare ground (J40).
* **Every agent is at LOD2** — 89 vehicles and 206 people, none at a nearer level — and **232 pedestrians were dropped for standing where the planimetric data has no sidewalk**, which at Domino Park is the esplanade.
* **Nine props across three kinds were wanted in range and have no asset**: 5 drinking fountain, 2 artwork, 2 misc structure.
* **The frustum reports the refinery composite at 182.0 m, 29.4° off axis**, which is the composite centroid rather than either the refinery or the park.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the reference is a photograph of flowers | the chooser matched the park's name and cannot tell a place from a plant in it (J93) | **verification — open, J93** |
| the camera stands on the river at 0.0 m | Domino Park's esplanade is a built deck and the 2013 bare-earth heightmap carries none of it, so the eye point sits over the water; the record names the raised surface and then uses the heightmap anyway. J85's family on a small deck, costing the camera position rather than the road | **geometry — open, measured** |
| no height, no tilt, no sightline | the highest built thing at the subject's coordinate is 0.3 m, under the 2 m threshold (J96) | **verification — open, J96** |
| the water is a flat mirror | water is a flattened surface at a single elevation with no wave or depth model | **declared scope** |
| the park's walkway, beds, tanks and crane track absent | the landmark model carries the refinery's massing; the park's own structures are not authored | geometry — declared scope |
| 971 props of 2,286 in range | the props triangle budget at 1,221,034, which dropped 1,202 | **performance** |
| 0 of 158 trees from modelled branches, 1,108 rows dropped, mean scale 0.835 | the props budget, and exported size classes that undersize the surveyed heights | performance + **data** |
| park ground missing on 3 tiles | not built for those tiles; the record names all three | **data — open, three tiles unbuilt** |
| 0.1945 of far park ground under the terrain, z-fighting 0.0494 | the terrain grid coarsens to 40 m beyond the near band (J85) | geometry — open, measured |
| nine park surface kinds flat-coloured | the texture catalogue has no photographic set for any of them (J40) | **declared decision** |
| every agent at LOD2, 232 pedestrians dropped off-sidewalk | the LOD rule picks by distance, and the esplanade is not a walkable surface in the planimetric data | performance + **data, open** |
| 9 props across three kinds unmapped | no asset exists for those kinds | data |
