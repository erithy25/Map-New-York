# Coney Island Cyclone

`landmark_coney_island_cyclone` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Coney Island Cyclone August 2022 001.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-08-12 13:54:26, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Coney_Island_Cyclone_August_2022_001.jpg) — the photograph's own view direction is derived from the image at **high** confidence.

**Camera** — 40.57523, -73.97779 (NYC_TM -2353, -13855) at z 3.6 m NAVD88 | azimuth 200.2°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1208x906. Position and heading both come from the photograph: its own EXIF camera GPS, **53.5 m** from the item's recorded viewpoint, and 200.2° is the bearing from there to the subject. The item's recorded azimuth of 225.4° is 25.2° away. **The lens stayed at 35 mm and the axis stayed level, and the record says why**: nothing built stands within 6 m of the subject's coordinate, so its mid-height is not known and there is nothing to tilt towards. The camera was not moved — open air, azimuth clear for **87.0 m** against the 25.5 m needed — and the nearest built thing is `lm_b_coney_island.0` **25.0 m** away. Ground under the camera reads **1.961 m** NAVD88, the 10th percentile of **113** heightmap samples within 12 m, range 1.82 to 2.18 m.

**Sun** — azimuth 208.2°, elevation 61.7° at 2022-08-12T13:54:26−04:00, from the photograph's own **EXIF DateTimeOriginal**; 922.8 W/m² direct normal, sky at strength 0.0309, Filmic, **+0.08 stops**. This is the **smallest development in the pass**: the linear frame's median is **0.17072** against a middle-grey target of **0.18**, so the scene arrived within a twelfth of a stop of a photographable level on its own (J83). The physical rule would have given 0.0.

**In the scene** — 1,857,799 triangles: 4 building tiles (70,048 tris, none missing, none LOD-substituted), 1 landmark model, in the frame, 12,159 pavement polygons with **0 dropped**, 823 props, 2,870 kit pieces, **0 park-ground meshes**, 4 structures tiles with **none missing** (49,480 tris), 47 vehicles and 203 people, terrain 81,608 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the Cyclone's timber frame is modelled as a repeating row of bents with no track, no lift hill and no diagonal bracing, and the item's own subject coordinate has nothing under it, so this sheet carries no verdict

**The subject coordinate is empty.** The probe cast 43 rays and **0** found built fabric: *nothing built stands within 6 m of the subject's coordinate; the nearest built thing is `t_-3_-14_tan_brick`, 21 m away at bearing 338 deg*. With no measured height there was no tilt and no widened lens, and **no sightline was tested**, so this sheet has no `subject_visible_fraction` at all. It is one of the 13 records in that state, recorded as **J96**, and here the cause is the third kind: the Cyclone is a track, not an object, so there is no single point that carries its fabric.

**The structure that is modelled is a picket row.** Down the left of the frame stands a long pale timber lattice of evenly spaced vertical bents — recognisably the Cyclone's supporting frame, and correctly pale unpainted pine. What it carries is nothing: no track, no lift hill profile, no diagonal cross-bracing between the bents, no station, no signage. The reference is the opposite: the frame seen from beneath at close range, dense with diagonals, the track curving overhead, the vertical CYCLONE sign and the 95 YEARS banner filling the upper right.

**What the render does get is the neighbour.** The Wonder Wheel stands on the right with its rim, spokes and **red, yellow and blue cars** in the right places and the right colours — the most convincing single object in this queue, and it is not this sheet's subject.

**The exposure is the best in the pass and the colour is the worst-matched part.** +0.08 stops metered, mean **0.984×** and median **0.941×** against the photograph. Chroma **0.065** against **0.2616**, a ratio of **0.248**: the reference is a deep blue August sky with one white cloud, and a yellow-and-black sign; the render has a pale grey-blue gradient sky, bare asphalt and pine.

## What matches

* **The development is the smallest in the pass**, +0.08 stops from a median linear luminance of 0.17072 against the 0.18 target — a scene already lit like its photograph (J83).
* **The mean and the median are within 2 and 6 per cent** — 0.984× and 0.941× — and the two development offsets are **0.189 stops** apart.
* **The Cyclone's bents are there, at the right spacing and in the right timber colour.**
* **The Wonder Wheel is modelled with its coloured cars** and reads correctly at this distance.
* **Every structures tile in range has a file** — 4 of 4, **49,480 triangles**.
* **Neither kit nor props were capped**: 2,870 kit pieces of 2,947 in range with 77 suppressed under the landmark shell, and 823 props of 881.
* **The record refuses to invent a height** — 0 of 43 rays reported, the 21.0 m offset named, no lens change and no sightline claimed (J74, J96).
* **The pavement is complete**: 12,159 polygons, **0 dropped**, including 3,425 sidewalk, 2,557 white markings, **2,494 parking lot** and 2,196 roadbed — a parking-heavy mix that is right for Surf Avenue.

## What does not match

* **The subject coordinate has no fabric under it**, 21.0 m from the nearest built thing, so there is no height, no extent and no sightline verdict (J96).
* **The Cyclone has no track and no bracing.** A row of bents without the structure they exist to hold.
* **No signage at all** — neither the vertical CYCLONE sign nor the banner, which between them are half the reference.
* **Chroma is 0.248 of the photograph's**, 0.065 against 0.2616.
* **Contrast is 0.614 of the photograph's**, and the render's fifth percentile is **0.3437** against **0.1372** — nothing in the render's frame is dark, where the reference's whole subject is a timber lattice in its own shadow.
* **No cloud and a pale sky.** The reference's deep blue with a single cumulus is a Nishita dome at strength 0.0309.
* **No park ground at all** — 0 meshes — and the record names **4 tiles** inside the 554 m ground radius for which it was not built, so those render as bare terrain.
* **Only 27 of 533 trees are drawn from modelled branches**; **364** species were substituted, **2** instances scaled out of band and 5 cards dropped.
* **Twenty-eight props across eight kinds were wanted in range and have no asset**, **14 of them parks buildings** — at Coney Island that is the ride buildings, the ticket booths and the comfort stations. 5 billboard, 3 misc structure, 2 drinking fountain, 1 artwork, 1 memorial, 1 parks comfort station, 1 vending machine.
* **Two hundred and three people and 47 vehicles** on a Friday in August. The table asked for 177 people and 105 vehicles and 358 and 140 were simulated, so the shortfall here is the drawing radius rather than the budget — but Coney Island in August does not look like 203 people.
* **The frustum reports the Coney Island composite at 147.4 m, 25.1° off axis**, which is the composite centroid rather than the Cyclone.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the subject coordinate has no fabric under it | the Cyclone is a track, not a point object; the stored coordinate sits 21.0 m from the nearest built thing and the probe's reach is 6 m, so the chain reports the miss and tests nothing (J96) | **data + verification — open, J96** |
| no track, no lift hill, no bracing | the landmark builder models the bents and not the ride; a roller-coaster track is not a class it authors | **geometry — declared scope** |
| no signage | signage on a landmark shell is not placed from any source, and the honesty rule forbids inventing copy (DATA_CONTRACTS 6.1.1, DEVIATIONS B15a) | **declared decision** |
| chroma 0.248×, p05 0.3437 against 0.1372, sd 0.614× | no sky colour, no deep shadow inside the lattice, and a flat-coloured frame | reference + consequence |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
| no park ground, 4 tiles unbuilt | park ground was not built for those tiles; the record names all four | **data — open, four tiles unbuilt** |
| 27 of 533 trees from modelled branches, 364 species substituted | the props budget spends its triangles on cards at this density, and the tree catalogue does not hold most species surveyed here | performance + **data** |
| 28 props unmapped, 14 of them parks buildings | no asset exists for those kinds, and at Coney Island that kind is the ride buildings | **data — open** |
| 203 people in August | the drawing radius rather than the budget; nothing was dropped for the agent triangle budget on this sheet | verification |
| the composite reported 25.1° off axis | the frustum test uses a landmark composite's centroid | verification — open |
