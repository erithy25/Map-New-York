# Arthur Ashe Stadium

`landmark_arthur_ashe_stadium` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:2021 US Open, Day 21.jpg by Curlyrnd, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2021-08-30 12:57:38, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:2021_US_Open,_Day_21.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.74978, -73.84727 (NYC_TM 8676, 5533) at z 12.2 m NAVD88 | azimuth 59.8°, pitch +2.8° | 35 mm on 36 mm (54.4° horizontal) | 1208x906. Position and heading both come from the photograph: its own EXIF camera GPS, **239.5 m** from the item's recorded viewpoint — inside the 250 m rule, but barely — and 59.8° is the bearing from there to the subject. The item's recorded azimuth of 120.0° is **60.2° away**. The lens stayed at 35 mm and the axis was tilted **+2.8°** to the subject's mid-height, because the object standing at the subject's coordinate is only 6 m tall. **The camera was raised onto the landmark's own deck** (J65): the eye point sat **4.38 m under** `lm_c_usta_arthur_ashe.0`, the model's level deck at **10.57 m** NAVD88, so it was lifted to stand on the surface actually drawn under it at **12.17 m** NAVD88. The camera was not otherwise moved — there is no nominal viewpoint to walk to, since this position is the photograph's own fix. The azimuth is clear for **64.1 m** and the nearest built thing is that same deck, **4.4 m** away at −9.1° yaw and −21.1° pitch.

**Sun** — azimuth 180.8°, elevation 58.0° at 2021-08-30T12:57:38−04:00, from the photograph's own **EXIF DateTimeOriginal**; 913.5 W/m² direct normal, sky at strength 0.0312, Filmic, **+0.96 stops and not clamped**. The linear frame's median is **0.092731** against a middle-grey target of 0.18 — about a stop under, and the closest of the Queens sheets (J83). The physical rule would have given **0.0 stops**.

**In the scene** — 3,215,884 triangles: 7 building tiles (182,468 tris, none missing, none LOD-substituted), 4 landmark models of which 1 falls inside the 54.4° frame, 15,935 pavement polygons with **0 dropped**, 2,459 props, 3,674 kit pieces, 34 park-ground meshes over 613 surfaces with **11,617 faces cut** for landmark ground, 6 structures tiles (63,528 tris), 87 vehicles and **35 people**, terrain 87,758 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the reference is a photograph taken from inside the stadium during a match; the render is the outside of it, and the probe measured a six-metre deck for a forty-six-metre building

**The two halves have nothing in common.** The photograph looks down from the stands onto the blue court: crowd in rows, sponsor boards, players, the upper tiers full. The render stands on the plaza outside at eye level, looking at grey concrete with slot openings in it. The item is marked as an exterior subject and the chosen photograph is an interior — the same reference-selection fault recorded as **J93**, which counts three such items across the set, this one among them.

**And the measurement that certifies the frame is measuring the wrong object.** The probe reports **6.24 m** above a ground of 4.33 m, over **43 of 43** rays, on `lm_c_usta_arthur_ashe.0` — while the catalogue entry **1.3 m away** carries **46.0 m**. That is a ratio of **0.136**, the second lowest in the whole pass: only Pier 57, at 0.104, is further out. The object at the subject's coordinate is the stadium's plaza deck, extent **154.2 m by 153.6 m** — the footprint, not the building. Because 6 m is under the 12 m floor, the sightline fan fell back to the floor, aimed at **3.0 m above the deck**, and returned **13 of 13 rays clear with 12 on the subject**, visible fraction **0.923**.

**So 0.923 is true and misleading at once.** Twelve rays do land on `lm_c_usta_arthur_ashe.0`. What they land on is a slab four metres from the lens. Nothing in the verdict distinguishes seeing the deck of a stadium from seeing the stadium, and this sheet is the extreme case of **J94** in the pass.

**The tonal figures are equally beside the point.** Chroma **0.0364** against the photograph's **0.1704**, a ratio of **0.214**, because the reference is a blue court, green surrounds, sponsor colour and several thousand items of clothing, and the render is bare concrete. The median runs the other way — **1.268×** — since the render's frame is uniformly mid-grey and the photograph has a deep shaded stand in it.

## What matches

* **The deck rule worked as designed** (J65): the record detected that the eye point sat 4.38 m below the landmark's own drawn deck and raised the camera onto it, naming both elevations.
* **The height probe is complete on the object it found** — 43 of 43 rays — and the record does not silently substitute the catalogue's 46.0 m for the 6.24 m it measured (J74). The figure it reports is the figure it measured.
* **The development is metered and unclamped**, +0.96 stops from a median linear luminance of 0.092731.
* **Near and mid-field ground are sound**: within 150 m, **0.0** of 269 park-surface samples sit under the terrain; between 150 and 400 m, **0.0558** of 233, minimum −0.531 m.
* **The landmark-ground rule did substantial work**: **11,617** park-ground faces cut where the landmark supplies its own ground, over 613 surfaces.
* **The woodland canopy rule contributes properly here**: **430** of the 1,938 impostor cards are procedural canopy stems inside mapped woodland polygons — this is Flushing Meadows, and the rule is doing what it was built for (J86's repair).
* **Props were not capped**: 2,459 placed of 2,561 in range, 0 dropped for the budget.
* **The kit was not capped either**: 3,674 placed of 4,874 in range, with 1,200 suppressed where the landmark shell stands in place of the tile's buildings.
* **The pavement is complete**: 15,935 polygons, **0 dropped**, including 3,756 white markings, 3,551 roadbed, 2,535 curb, 2,289 parking lot and 2,181 plaza — a parking-and-plaza mix that is right for this site.

## What does not match

* **The reference is an interior and the item is an exterior.** No render of the outside of this building can match a photograph taken from the stands.
* **The probe measured 6.24 m for a subject whose catalogue entry, 1.3 m away, carries 46.0 m** — ratio **0.136**, second lowest in the pass behind Pier 57's 0.104.
* **The visible fraction of 0.923 certifies a view of the deck**, not of the stadium, because the aim fell to 3.0 m above that deck.
* **Chroma is 0.214 of the photograph's**, 0.0364 against 0.1704.
* **Thirty-five people.** The density table asked for **318** and 363 were simulated; the render draws 35, all at LOD2, on a sheet whose reference contains a full stadium. Even at full strength the simulation has no rule that puts a crowd inside a stadium.
* **Eighty-seven vehicles, all at LOD2**, and the parking lots read as empty asphalt.
* **Sixty-six props across six kinds were wanted in range and have no asset**, and **36 of them are parks buildings** — at the National Tennis Center that is the ancillary courts, offices and stands. 12 misc structure, 6 artwork, 6 drinking fountain, 5 memorial, 1 parks comfort station.
* **Only 15 of 1,953 trees are drawn from modelled branches**, 1,938 are cards, **1,342** species were substituted, **2** instances scaled out of band and 3 cards dropped.
* **One of 6 structures tiles in range has no structures file.**
* **Beyond 400 m the park surface sits under the terrain on 0.3051 of 1,075 samples**, minimum **−2.152 m**, with a z-fighting fraction of **0.0502** — the highest in this queue — after a redrape that moved **427,031** vertices (J85).
* **Ten park-ground surface kinds fall back to the builder's flat colour** — infield dirt, cemetery grass, sport court, golf grass, grass field, greenstreet grass, park grass, pool water, recreation grass, bare ground — the most on any sheet in the queue, and on this site the sport courts are the subject matter (J40).
* **The render has no deep shadow at the fifth percentile** — 0.0538 against 0.0765 — and no highlight either: ninety-fifth percentile **0.6232** against **0.8565**.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| an interior reference for an exterior item | the chooser matches on place and subject terms and has no evidence of whether a photograph is inside or outside the thing (J93) | **verification — open, J93** |
| probe 6.24 m against a 46.0 m catalogue entry 1.3 m away | the probe takes the object standing at the subject's coordinate, and at a stadium that object is the plaza deck; ratio 0.136, second lowest in the pass (J94) | **verification — open, J94** |
| a visible fraction of 0.923 that certifies the deck | the fan fell back to the 12 m floor because the measured subject is 6.0 m, so the aim went to 3.0 m above the deck and the rays landed on it (J78 applied to the wrong object) | **verification — open, J94** |
| chroma 0.214×, p05 and p95 both compressed | bare concrete against a full stadium; nothing here is a statement about the build's colour | consequence of the reference |
| 35 people where the table asked 318 | the placement rules put pedestrians on walkable surfaces near roads, and there is no rule that seats a crowd inside a stadium | **verification — open, measured** |
| 36 parks buildings unmapped | no asset exists for that kind, and at this site that kind is most of the built fabric | **data — open, measured** |
| 15 of 1,953 trees from modelled branches, 1,342 species substituted | the props budget spends its triangles on cards at this density, and the tree catalogue does not hold most species surveyed in Flushing Meadows | performance + **data** |
| 1 of 6 structures tiles without a file | no structures file was built for that tile | data — open |
| 0.3051 of far park ground under the terrain, z-fighting 0.0502 | the terrain grid coarsens to 40 m beyond the near band over a flat park where surface and terrain are within centimetres of each other, which is where z-fighting appears (J85) | geometry — open, measured |
| ten park surface kinds flat-coloured | the texture catalogue has no photographic set for any of them (J40) | **declared decision** |
| 87 vehicles all at LOD2, empty parking lots | the LOD rule picks by distance; parked cars are not a class the fleet places | performance + **declared scope** |

## Measured for this assessment

One figure above is not in the render record. The record carries both heights — the probe's 6.24 m and
the catalogue's 46.0 m at 1.3 m away — and their ratio is what places this sheet in the survey behind
J94, so I divided them and checked the result against the same ratio computed for every render record
under `docs/verification/comparison` that carries a height probe.

| figure | where it comes from |
|---|---|
| 0.136 | 6.24 divided by 46.0, the second lowest such ratio among the 16 records whose probe height falls below three quarters of a catalogue entry within 20 m; Pier 57's 0.104 is lower |
