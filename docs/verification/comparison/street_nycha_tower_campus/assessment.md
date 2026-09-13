# NYCHA tower-in-the-park campus

`street_nycha_tower_campus` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:NYCHA Alfred E. Smith Houses 003.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2023-01-17 12:49:58, 1280x1707. [Commons page](https://commons.wikimedia.org/wiki/File:NYCHA_Alfred_E._Smith_Houses_003.jpg) — camera GPS on the file. One Alfred E. Smith Houses slab from close and below: a cruciform red-brick tower of about fifteen storeys, windows in unbroken vertical strips with dark frames, a plain parapet and no cornice anywhere, a bare tree across the bottom right, a white January sky behind — and **a window air-conditioner in perhaps a third of the openings**, which is most of what the elevation's texture is.

**Camera** — 40.70855, -73.999222 (NYC_TM -4178, 933) at z 3.048 m NAVD88, a 1.6 m standing eye over terrain read at 1.448 m. The ground rule is not the usual one: **16 samples within 5.0 m** rather than 113 within 12.0, because *"the viewpoint note names the raised surface the photographer stood on, so the heightmap height at the point itself is the ground"* — a terrace beside the Brooklyn Bridge approach can stand metres above the plaza four metres away, and a median across that step would put the camera underground. | azimuth 10.6°, pitch 0.0° | 35 mm on 36 mm, **portrait**, 42.163° horizontal by 54.432° on the long side | 904x1206, shaped to the reference's own 3:4. Position and heading both come from the photograph: its EXIF GPS, **140 m** from the item's recorded viewpoint, and the bearing from that fix to the subject, **2.0°** from the item's recorded azimuth. The walk then moved **25.2 m** onto a crosswalk polygon — *"boxed in: the view azimuth is closed off 41 m ahead, less than the 80 m this frame needs to show its subject"* — and from there the view is clear for **91.6 m** with **nothing built within 20 m of the lens**.

**Sun** — azimuth 191.6°, elevation 27.8° at 2023-01-17T12:49:58-05:00, from the photograph's own EXIF DateTimeOriginal; 749 W/m² direct normal, Nishita sky, Filmic, **+2.96 stops**. Metered: **2.961 stops** on a linear median of **0.023116** against a physical rule of 0.63. 17 January is inside the leaf-off window and both halves have bare trees.

## Verdict — the closest fabric match of any street sheet in the pass, and the instrument found a lawn where the subject is

**Put the two halves side by side and they are the same architecture.** Red-brown brick slabs of a dozen-odd storeys, punched windows in unbroken vertical strips, a flat parapet, no cornice, no string course, no ornament of any kind, standing apart from each other across open ground with bare trees between them and parking at their feet. That is what a tower-in-the-park campus is, and the render draws it without having to be told: the towers are ordinary tiled building shells from the same 10 building tiles as everything else, and the reason they read correctly is that NYCHA's architecture is the one kind this build's massing-plus-window-grid can represent exactly. **This is the closest agreement on fabric of any streetscape sheet read this round.**

**The air-conditioners are modelled, placed, and two pixels wide.** A third of the photograph's windows carry a through-window unit, and this build has five of them: `acc_ac_window_small`, `_medium` and `_large`, `acc_ac_bracket` and `acc_through_wall_ac_unit`, all in the kit's `window_accessory` category. They are placed in bulk on this tile — **6,490 of its 6,519 window accessories are air-conditioners** — and this scene drew **417** of them. What defeats them here is range: the subject stands 355 m from the lens and `acc_ac_window_medium` is 0.568 m across, so it subtends **0.092°**, which on a 904-pixel frame of 42.163° is **two pixels**. The pattern that makes the photograph's elevation look inhabited is in the model and below this sheet's resolution.

**The height probe measured a lawn, and it was right to.** `subject.height_probe.object` is **`t_-5_1_park_recreation_grass`** and the record says what follows: *"the highest built thing at the subject's coordinate is `t_-5_1_park_recreation_grass`, 0.5 m above the ground there -- below the 2 m at which a subject has a height worth aiming or framing by, so the lens was not widened to contain it"*, and *"no sightline"* was tested. Only **21 of 43** probe rays found built fabric at all. The coordinate of a tower-in-the-park campus **is** the park: the point that names the Alfred E. Smith Houses falls on the recreation grass between its slabs, which is a true statement about the place and leaves the sheet with no height, no fan and no visible fraction for fifteen-storey buildings that fill its frame. This is the Unisphere's fault in a new costume — there the probe found the fountain pool, here the campus lawn — and on this sheet it is arguably the correct answer to the wrong question.

**J74's radius did its job.** The nearest catalogue entry is the **Municipal Building, 463.3 m away and 177.1 m tall**, and `within_120_m` is **false**, so the rule refused to borrow a height from a different building four blocks off. A silent version of this pipeline would have published 177.1 m for a housing project.

**The tone is close and the colour is not.** The exposure gap is **0.544 stops** with the render brighter and a p50 ratio of **1.192**. Contrast runs **0.735** because the photograph's sky is clipped white — its 95th percentile is exactly **1.0** against the render's 0.8619 — and chroma **1.536**, the render carrying half again the photograph's colour: a January overcast desaturates brick and a clear Nishita sky with a 27.8° Sun on it does not.

**The scene is one of the most complete in the pass.** **10 of 10 building tiles** with none missing and none LOD-substituted; **38,179 pavement polygons** with 16,432 white markings, 9,656 roadbed, 5,137 curb, 3,232 sidewalk, 1,275 parking lot and 1,079 crosswalk, none dropped — and the roadbed outweighing the sidewalk three to one is exactly right beside the FDR and the bridge approach; **111,608 triangles of structures over 7 tiles** with 3 lacking a file, the largest structures contribution of any streetscape sheet here; **14 landmark models placed**, none of them inside the 42.2° frame; 103,966 triangles of terrain with 8 water bodies and no holes; and **53,345 park-ground faces cut for landmark ground**, the largest cut read this round.

**Of 123 park-ground samples within 150 m, none sits below the terrain**, the tightest clearing by **0.113 m**; beyond 400 m, where the grid coarsens to 40.0 m, 35 per cent of 2,125 sit under it and the worst is **-8.404 m**.

**What the budgets took.** Props: **719 placed and 5,383 dropped**, 88 per cent, one of the largest drop fractions in the pass, of which **4,641 are tree rows**. Kit: 3,101 pieces of 12,006 in range under a 626,653-triangle cap, including 6 antennas — a category that belongs on these roofs. And **264 of the 277 surviving trees had their species substituted**, 95 per cent, far above the pass-wide 39.19 per cent (J108).

**And 1,130 pedestrians were dropped standing in the carriageway without crossing** — the largest such figure read this round, with 313 more not on a walkable surface and 22 above the observer, against 283 drawn.

## What matches

* **The architecture**: brick slabs, vertical window strips, flat parapets, no ornament, standing apart across open ground.
* **The site plan**: towers set back from the street with parking and lawn between them, and a roadbed three times the sidewalk area.
* **The bare trees**, correct for 17 January in both halves.
* **Position and heading both from the photograph**, and the heading within 2.0° of the item's own.
* **J74 refused a catalogue height 463.3 m away** and published none rather than a wrong one.
* **The ground rule is the right one for a terrace beside a bridge approach**, and says why.
* **Building tiles complete**: 10 of 10, 296,450 triangles.
* **Structures substantial and named**: 111,608 triangles over 7 tiles.
* **Nothing under the terrain within 150 m**: 0 of 123 samples, tightest clearance +0.113 m.
* **6 antennas** on the roofs, which is where NYCHA puts them.
* **417 window air-conditioners placed**, from a catalogue of five, though at 355 m each is two pixels wide.

## What does not match

* **The subject probe found a lawn** 0.5 m tall, so this sheet publishes no height, no fan and no visible fraction for the buildings that fill it.
* **Chroma 1.536 and contrast 0.735**: a clear sky and a 27.8° Sun against a clipped-white January overcast.
* **0.544 stops brighter** with a p50 ratio of 1.192.
* **88 per cent of the props dropped** — 5,383 of them, 4,641 tree rows — so the campus lawns are emptier than they are.
* **95 per cent of the surviving trees are the wrong species** (J108).
* **1,130 pedestrians dropped in the carriageway without crossing**, against 283 drawn.
* **No signage of any kind** (J110), and no NYCHA development sign, which is on every one of these campuses.
* **Four boro taxis below 96th Street** (J105).
* **Three of the ten structures tiles have no file.**

## Measured for this assessment

| figure | where it comes from |
|---|---|
| the kit has five window air-conditioner assets and 6,490 of this tile's 6,519 window accessories are one of them | the `window_accessory` entries of `data/processed/kit_catalog.json`, counted against the `kit_id` column of `data/processed/tiles/t_-5_1/kit_placements.bin` |
| `acc_ac_window_medium` is 0.568 m across and subtends 0.092 deg at 355 m, two pixels on a 904-pixel frame of 42.163 deg | accessor bounds of `blender_out/kit/facade/acc_ac_window_medium.glb` against the record's own subject distance and frame |
| 3,101 kit pieces | the sum of the record's `scene.kit.per_category`, whose `total` is null |
| 264 of 277 trees substituted is 95 per cent, against a pass-wide 39.19 per cent | the record's `props.tree_species_substituted` and its tree count, with the pass-wide figure from DEVIATIONS J108 |
| 88 per cent of props dropped is among the largest fractions in the pass | the `props.placed` and `dropped_for_budget` of every record in the pass, ranked |
| this is the closest agreement on building fabric of any streetscape sheet read this round | comparing both halves of this sheet against the other streetscape sheets read in this round on massing, window rhythm, parapet and ornament |
| 17 January is inside the leaf-off window | the `leaf_off` rule in `blender/verify/render_sheets.py` (J97) |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the probe measured a lawn | a campus's subject coordinate falls on the open space its towers stand in, and the probe takes whatever is highest at that point; below 2 m it declines to frame, aim or test a sightline | **verification — open, and the correct answer to the wrong question** |
| chroma 1.536, contrast 0.735 | a clear procedural sky against a clipped-white overcast; nothing in this build reads a historical sky | reference — no source exists |
| 88 per cent of props dropped | a 920,051-triangle prop cap against a campus whose open ground carries 4,641 tree rows | performance — declared |
| 95 per cent of trees the wrong species | ten species with two appearances each against the 132 the 2015 street-tree census counts (J108) | content — open |
| 1,130 pedestrians in the carriageway | the crowd is placed on the road network and only sidewalk, median, plaza and crosswalk surfaces are walkable, so a campus's interior paths carry people the placer cannot keep | **runtime — open** |
| no signage, and no NYCHA development sign | the verification renderer never reads the sign or signal export, and no lettering exists on any surface (J110) | **verification — open** |
| four boro taxis below 96th Street | `TrafficSim::sampleClass` splits the taxi share with no geography (J105) | **runtime — open** |
| three of ten structures tiles have no file | the B13 remainder | data — open |
