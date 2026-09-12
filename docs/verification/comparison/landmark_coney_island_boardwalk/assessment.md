# Riegelmann Boardwalk, Coney Island

`landmark_coney_island_boardwalk` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Ruby's Bar & Grill (Coney Island) AB.jpg by Chepry (Andrzej Barabasz), CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-04-28 13:12:12, 1920x1280. [Commons page](https://commons.wikimedia.org/wiki/File:Ruby%27s_Bar_%26_Grill_(Coney_Island)_AB.jpg) — the photograph's own view direction was **not** derived from the image; confidence is **medium**.

**Camera** — 40.57323, -73.97987 (NYC_TM -2529, -14077) at z 6.8 m NAVD88 | azimuth 70.0°, pitch +0.0° | 35 mm on 36 mm (54.4° horizontal) | 1280x854. The camera stands on this photograph's own EXIF camera GPS, **100.6 m** from the item's recorded viewpoint. The azimuth is **70.0° as recorded in `meta.json`**, and the record is explicit about what that costs: *This item names no subject and the reference photograph's own view direction was not derived from the image (confidence: medium), so the two halves of this sheet are not guaranteed to face the same way — compare them on street width, storey height and material, not on composition.* The lens stayed at 35 mm and the axis level, because there is no subject to aim at. **The camera was raised onto the boardwalk's own deck** (J65): the eye point sat **0.05 m under** `lm_b_coney_island.51`, the model's level deck at **5.20 m** NAVD88, so it was lifted to stand on the surface actually drawn under it at **6.80 m** NAVD88 — the smallest deck correction in the pass, and the record still states it. The azimuth is clear for **75.9 m** and the nearest built thing is that deck, **4.9 m** away.

**Sun** — azimuth 190.2°, elevation 63.4° at 2022-04-28T13:12:12−04:00, from the photograph's own **EXIF DateTimeOriginal**; 926.5 W/m² direct normal, sky at strength 0.0308, Filmic, **+0.41 stops and not clamped** — the second-smallest development in this queue. The linear frame's median is **0.135646** against a middle-grey target of 0.18; the physical rule would have given **0.0 stops** (J83).

**In the scene** — 1,161,283 triangles: 6 building tiles (102,188 tris, none missing, none LOD-substituted), 1 landmark model and **0 of it inside the 54.4° frame**, 7,319 pavement polygons with **0 dropped**, 1,095 props, 960 kit pieces, **0 park-ground meshes**, 6 structures tiles with **none missing** (51,412 tris), 27 vehicles and 36 people, terrain 91,586 tris at 2.0 m near / 40.0 m far with no holes.

## Verdict — the boardwalk is modelled as a smooth pale surface with no boards in it, and this sheet has no subject, no height probe and no sightline verdict at all

**The item names no subject, so two thirds of the verification chain did not run.** The record says it plainly: *the item names no point subject*. There is no height probe, no plan extent, no sightline, no visible fraction. What is left is the frame's own statistics and the scene inventory — which is the correct behaviour for an item that names a stretch of deck rather than a thing, and it means this sheet cannot be scored the way a landmark sheet is.

**The deck is modelled and has no boards in it.** The boardwalk itself is real geometry: `blender/landmarks/b_park_lib.py` builds a *timber boardwalk deck following a real polyline, on piles, with a handrail*, and the render shows that handrail running away down the left of the frame. What the deck does not have is a plank pattern. Its material, `wood_deck` in `blender/landmarks/b_common.py`, is an analytic base colour of (0.45, 0.33, 0.20) at roughness 0.8, with the reference *Ipe/pine boardwalk & promenade planks* written into the entry and no texture behind it. So the surface is one flat tone, and the herringbone bays, joints, wear and colour variation that identify the Riegelmann Boardwalk are all absent — at +0.41 stops under a 63° sun that flat brown reads as pale tan.

**Ruby's is not in the frame and the record warns that it might not be.** The photograph is a red-painted storefront photographed head-on: the sign, the awning line, the folding glass fronts, the chairs on the deck. The render looks along the deck instead, at a timber railing, a roller coaster's white lattice in the middle distance and a row of low brick blocks. The chooser had medium confidence and no derived view direction, and the record told the reader to compare on width, storey height and material rather than composition — which is the right instruction and is why this sheet is honest rather than wrong.

**On those terms it half succeeds.** The deck's width, the railing, the coaster's lattice and the low commercial blocks along the north side are all in roughly the right place and at roughly the right scale. What is missing is everything that makes it Coney Island: the paint, the signs, the crowd and the plank pattern.

## What matches

* **The deck rule worked to five centimetres** (J65): the eye point sat 0.05 m under the model's own deck at 5.20 m NAVD88 and the camera was raised onto the surface drawn at 6.80 m, with both elevations recorded.
* **The record declares the weakness of the pairing up front** — no derived view direction, medium confidence, no named subject — and tells the reader what can and cannot be compared.
* **The development is nearly physical**: +0.41 stops from a median linear luminance of 0.135646, three quarters of the way to the 0.18 target on its own.
* **Every structures tile in range has a file** — 6 of 6, **51,412 triangles** — and the boardwalk's own deck is among them. This is the best structures coverage in the queue.
* **The railing, the deck width and the coaster lattice are in the right places** at the right scale.
* **The kit was not capped**: 960 placed of 1,101 in range, with 141 suppressed under the landmark shell — and **storefront is the largest category at 344 pieces**, so the shopfronts exist on this block, just not on the faces in this frame.
* **Props were not capped**: 1,095 placed of 1,157 in range.

## What does not match

* **The deck has no plank pattern.** One flat tone from an analytic `wood_deck` colour, where the reference is herringbone timber decking with visible joints and wear.
* **There is no subject, no probe and no sightline** — three of the chain's measurements are absent by construction.
* **Ruby's, its paint and its signs are not in the frame**, and neither is any other storefront face.
* **Chroma is 0.302 of the photograph's**, 0.1046 against 0.3464 — the reference is a red building under a deep blue April sky; the render has pale deck, brown railing and grey sky.
* **The render is brighter and flatter**: mean **1.342×**, median **1.264×**, standard deviation **0.777×**, and a fifth percentile of **0.2428** against **0.0801**.
* **Thirty-six people and 27 vehicles.** The table asked for 158 people and 72 vehicles; 219 and 95 were simulated, and **70 pedestrians were dropped for standing where the planimetric data has no sidewalk** — on a boardwalk, that is the boardwalk.
* **Park ground was not built for 6 tiles** inside the 821 m ground radius, so the beach and the park strips render as bare terrain. **0 park-ground meshes exist in the whole scene.**
* **Only 2 of 755 trees are drawn from modelled branches**; **483** species were substituted, **2** instances scaled out of band and 2 cards dropped.
* **Thirty props across seven kinds were wanted in range and have no asset**: 8 parks building, 5 billboard, 5 vending machine, 4 drinking fountain, 4 misc structure, 3 parks comfort station, 1 artwork. On this boardwalk the parks buildings are the comfort stations and the concession blocks, and the vending machines and billboards are the trade itself.
* **No landmark model falls inside the frame** — 1 placed, **0 in the cone** — so the Wonder Wheel and the aquarium the viewpoint note names are both outside it.
* **The sky is a flat grey-blue gradient** where the reference is a saturated clear blue, and nothing in this build reads a historical sky.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the deck has no plank pattern | the deck geometry and its handrail are built from the real polyline, but `wood_deck` is an analytic colour with no texture behind it, so the boards are named in the material's own reference string and not drawn (J40's family, on the surface that is the subject) | **data — open, measured** |
| no subject, no probe, no sightline | the item names no point subject, and the chain correctly does not invent one | **declared behaviour** |
| Ruby's is not in the frame | the reference has no derived view direction and medium confidence, and the item's recorded azimuth points along the deck instead; the record states the limit rather than implying a match | **verification — declared** |
| chroma 0.302×, p05 0.2428 against 0.0801 | no paint, no signage and no deep blue sky in the render's frame | consequence of the rows above + reference |
| 36 people on a boardwalk | 70 pedestrians dropped for standing where the planimetric data has no sidewalk, which here is the boardwalk itself | **data — open, measured** |
| no park ground at all, 6 tiles unbuilt | park ground was not built for those tiles; the record names all six | **data — open, six tiles unbuilt** |
| 2 of 755 trees from modelled branches, 483 species substituted | the props budget spends its triangles on cards at this density, and the tree catalogue does not hold most species surveyed here | performance + **data** |
| 30 props across seven kinds unmapped | no asset exists for those kinds, and on this boardwalk those kinds are the concessions | **data — open** |
| no landmark in the frame | the item's recorded azimuth looks along the deck, and the Wonder Wheel and aquarium lie outside a 54.4° frame from this point | verification |
| a flat sky | nothing in this build reads a historical sky | reference — no source exists |

## Measured for this assessment

Three figures above are not in the render record. They come from the build's own source, because the
question this sheet raises — whether the boardwalk's boards exist anywhere — can only be answered
there. Read with `blender/landmarks/b_common.py` and `blender/landmarks/b_park_lib.py`.

| figure | where it comes from |
|---|---|
| 0.45, 0.33, 0.20 | the `wood_deck` entry's `base_color` in `b_common.py`, whose `ref` field reads "Ipe/pine boardwalk & promenade planks" — a named reference with an analytic colour and no texture behind it |
| 0.8 | that entry's roughness |
| 2.032 | the tile length of `wood_clapboard`, the only timber entry in the shared photographic texture catalogue, which is a wall siding and not a deck |
