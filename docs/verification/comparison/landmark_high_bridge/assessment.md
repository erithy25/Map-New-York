# High Bridge

`landmark_high_bridge` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:High Bridge looking east.jpg by RoySmith, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2017-05-19 08:42:55, 1920x2090. [Commons page](https://commons.wikimedia.org/wiki/File:High_Bridge_looking_east.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.84234, -73.93099 (NYC_TM 1562, 15772) at z 7.2 m NAVD88 | azimuth 88.0°, pitch +0.0° | 35 mm on 36 mm (50.6° horizontal, 54.4° vertical, portrait) | 1002x1090. Position and heading both come from the photograph: its own EXIF camera GPS, **118.4 m** from the item's recorded viewpoint, and 88.0° is the bearing from there to the subject; the item's recorded azimuth of 77.9° is 10.1° away. **The lens stayed at 35 mm and the axis stayed level**, because nothing built stands within 6 m of the subject's coordinate — the nearest is `lm_b_high_bridge.3`, **21.0 m** away at bearing 180°. The recorded viewpoint was **boxed in** — the azimuth closed **6 m** ahead against the 80.0 m needed — so the camera was **moved 52.5 m** onto the nearest surveyed roadbed, and with no subject height to score against, `scored_on_subject_sightline` is **false**. From there the azimuth is clear for **96 m**, nothing built stands within 20 m of the lens, and no agent either. Ground under the camera reads **5.619 m** NAVD88 from 16 heightmap samples within 5.0 m, range 5.49 to 6.94 m.

**Sun** — azimuth 92.0°, elevation 33.6° at 2017-05-19T08:42:55−04:00, from the photograph's own **EXIF DateTimeOriginal**; 799.4 W/m² direct normal, sky at strength 0.0349, Filmic, **+1.39 stops and not clamped**. The linear frame's median is **0.068864** against a middle-grey target of 0.18; the physical rule would have given **+0.36 stops** (J83).

**In the scene** — 3,230,995 triangles: 7 building tiles (297,528 tris, none missing, none LOD-substituted), 1 landmark model, in the frame at **6.5° off axis**, 31,547 pavement polygons with **0 dropped**, 6,847 props, 396 kit pieces, 43 park-ground meshes over 599 surfaces, 5 structures tiles (26,472 tris) with **2 without a file**, 88 vehicles and 16 people, terrain 93,312 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the aqueduct is modelled well and the camera was moved fifty-three metres off the deck to underneath it, so the photograph looks along the walkway and the render looks up at the arch

**The bridge is good.** The render carries the 1928 steel arch in its correct green, the masonry arches of the original Croton Aqueduct viaduct marching away to the right, the deck with its lamp standards, and the piers going down to the water. As a piece of landmark geometry it is among the better things in this pass.

**And the frame is on the wrong side of it.** The reference stands **on** the deck: a brick-paved walkway between two iron railings, running east to a vanishing point, with the Bronx bank beyond. The render stands underneath and to the side. The cause is the same J96 chain seen elsewhere — the stored subject coordinate is **21.0 m** off the fabric it names, so 0 of 43 rays landed, no height was measured, the lens stayed at 35 mm, the axis stayed level, **no sightline was tested**, and the clearance walk then fell back to a pavement snap with no subject scoring. The recorded viewpoint was boxed in at 6 m, so the walk moved 52.5 m — and the only open roadbed near the Manhattan abutment is below the deck.

**The middle distance is the worst terrain in the pass.** Along the Harlem River bank the ground breaks into **jagged angular shards**, and the measurements say why: beyond 400 m the park surface sits under the terrain on **0.3268** of 1,120 samples, minimum **−9.009 m** against a maximum of **+7.692 m** in the same band, the widest spread in any single band in this pass, after a redrape that moved **884,157** vertices — the largest redrape in the pass (J85). Even within 150 m the under-fraction is **0.1304** over 115 samples, the worst near band in this queue.

**The canopy, by contrast, is the pass's best use of the woodland rule**: **4,367** of the 6,540 impostor cards are procedural canopy stems placed inside mapped woodland polygons — Highbridge Park's slope — and **0** cards were dropped.

**The colour comparison is void in one direction.** Chroma **0.0286** against the photograph's **0.0811** (**0.353×**): the render's frame is grey concrete, grey water and grey sky, with the arch's green the only saturated thing in it. The reference is warm brick underfoot and deep green canopy either side.

## What matches

* **The steel arch, the masonry arcade, the deck and the lamp standards** are all modelled, and the arch is the right green.
* **The woodland canopy rule is at its best here**: 4,367 procedural canopy stems of 6,540 cards, **0** dropped (J86's repair).
* **The kit was fully placed**: 396 of 396 in range, nothing capped, nothing suppressed.
* **Props were not capped**: 6,847 placed of 6,900 in range — the largest prop count in this queue.
* **The development is metered and unclamped**, +1.39 stops from a median linear luminance of 0.068864, against a physical rule of +0.36.
* **The landmark is in the frame** at 176.5 m, **6.5° off axis** — the frustum test agrees with the picture.
* **The record names every limit**: the 21.0 m coordinate offset, the untested sightline, the walk that was not scored on it, and the 6 m closure that forced the move.
* **The pavement is complete**: 31,547 polygons, **0 dropped**, including **17,596** white markings, 5,356 roadbed, 3,911 curb and 2,441 sidewalk.

## What does not match

* **The frame is under the bridge, not on it.** The photograph's subject is the walkway; the render's is the underside.
* **No height, no extent, no sightline verdict** (J96), and the clearance walk was not scored on the subject.
* **The riverbank terrain breaks into jagged shards**: minimum **−9.009 m** against a maximum of **+7.692 m** beyond 400 m, and **0.1304** under even within 150 m (J85).
* **Chroma is 0.353 of the photograph's**, 0.0286 against 0.0811 — the render's frame is almost monochrome.
* **The water is a flat mirror** on the Harlem River.
* **The deck's brick paving does not exist as paving.** The photograph is entirely brick pavers in a running bond; the render's deck is a flat surface, and the only timber or masonry surface entries in the shared catalogue are wall materials.
* **Two of 7 structures tiles have no structures file.**
* **Sixteen people and 88 vehicles**, with **89 pedestrians dropped for standing where the planimetric data has no sidewalk** — which on this item is the bridge deck itself, the one place people are.
* **Every agent is at LOD2.**
* **Fifteen props across four kinds were wanted in range and have no asset**: 7 misc structure, 5 parks building, 2 memorial, 1 parks recreation centre.
* **Nine park-ground surface kinds fall back to the builder's flat colour** (J40).
* **837 tree species were substituted** and 4 instances scaled out of band.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the frame is under the bridge | the stored subject coordinate is 21.0 m off the fabric it names, so no height was measured, the walk was not scored on the subject, and the 6 m closure then moved the camera 52.5 m to the only open roadbed nearby, which is below the deck (J96) | **data + verification — open, J96** |
| jagged riverbank terrain, from −9.009 m to +7.692 m in the same band | the terrain grid coarsens to 40 m beyond the near band across Highbridge Park's steep slope to the Harlem River; the redrape moved 884,157 vertices and cannot close it (J85) | **geometry — open, measured, and the worst instance in the pass** |
| chroma 0.353×, a near-monochrome frame | no brick, no canopy and no sky colour in the render's frame | consequence of the viewpoint |
| the water is a flat mirror | water is a flattened surface at a single elevation with no wave or current model | **declared scope** |
| the deck's brick paving is a flat surface | the shared photographic texture catalogue holds no paver or setted-surface entry; its masonry entries are wall materials (J40's family) | **data — open** |
| 2 of 7 structures tiles without a file | no structures file was built for those tiles | **data — open, two tiles unbuilt** |
| 16 people, 89 dropped off the walkable surface | the bridge deck is not a walkable surface in the planimetric data, and it is the one place people are on this item | **data — open, measured** |
| every agent at LOD2 | the LOD rule picks by distance and everything in range sits beyond the nearer bands | performance |
| 15 props across four kinds unmapped | no asset exists for those kinds | data |
| nine park surface kinds flat-coloured | the texture catalogue has no photographic set for any of them (J40) | **declared decision** |
| 837 species substituted, 4 scaled out of band | the tree catalogue does not hold most species surveyed here | data |
