# Robert F. Kennedy (Triborough) Bridge

`landmark_rfk_triborough_bridge` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Triborough Bridge td (2021-06-07) 01 - East River Span.jpg by Tdorante10, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2021-06-07 13:48:49, 1920x1280. [Commons page](https://commons.wikimedia.org/wiki/File:Triborough_Bridge_td_(2021-06-07)_01_-_East_River_Span.jpg) — the photograph's own view direction is derived from the image at **high** confidence. **It is taken from a moving car**: the bonnet fills the bottom edge, the frame is lane markings, a sign gantry, a cobra-head lamp standard, a Jersey barrier and two cars ahead. It is a driver's view on the approach, not a view of the suspension span.

**Camera** — 40.7795, -73.9255 (NYC_TM 2068, 8829) at z 1.6 m NAVD88 | azimuth 204.4°, pitch 0.0° | 35 mm on 36 mm (54.4° horizontal, landscape) | 1280x854. The camera stands on **the item's recorded viewpoint** — Astoria Park's shore path — because the record detected that the photograph's own GPS, 68 m away, puts the eye point **inside `lm_b_rfk_triborough.51`**, a ray straight up from it hitting the model's roof, which is the signature of a photograph taken on the bridge itself. The recorded azimuth of 204.4° agrees with the bearing to the subject to **0.1°**, and the axis was left level because the subject is 305 m off. The walk did not move it: 150.0 m of clear view against an 80.0 m requirement, nothing built within 60 m, no agent within 60 m. **The ground under it reads 0.0 m NAVD88** — 16 samples within 5 m, range 0.0 to 0.0 — so the eye sits 1.6 m above the tidal datum (J103).

**Sun** — azimuth 216.5°, elevation **68.7°** at 2021-06-07T13:48:49−04:00, from the photograph's own **EXIF DateTimeOriginal**; **936.3 W/m²** direct normal, the highest irradiance on any sheet written so far, sky at strength 0.0305, Filmic, **+0.87 stops** metered and unclamped against a linear median of **0.0983** and a target of **0.18**. The physical rule would have given **0.0 stops**.

**In the scene** — 1,429,652 triangles: 6 building tiles (205,270 tris, 0 missing, 0 LOD-substituted), 2 landmark models and **none in the 54.4° cone**, 14,328 pavement polygons, 1,621 props, **no facade kit in the frame**, **0 park-ground meshes**, 40,976 triangles of structures over 6 tiles with **none missing**, 42 vehicles and 63 people.

## Verdict — nothing about the bridge is measurable, because the coordinate the item records is 90 m from any built thing

**The probe cast 43 rays and found fabric on none of them.** The record's words: *nothing built stands within 6 m of the subject's coordinate; the nearest built thing is `t_1_8_red_brick`, **90.3 m** away at bearing 225°, so the coordinate the item records is that far off the fabric it names*. So there is no height, no plan extent and **no sightline** on this sheet — it is one of J96's thirteen, and the entry names it by this figure. The nearest catalogue origin, `b_rfk_triborough`, stands **297.6 m** away, past the 120 m the old rule looked in, so nothing was inherited either. The frustum lists **0 of 2** placed landmarks in the cone. Every measurement this sheet could have carried about its subject is absent, and the record says why in each case.

**The camera is standing on water in a park that has no ground.** The ground sample reads **0.0 m NAVD88** over its whole neighbourhood, the tidal datum (J103), so the lower half of the render is a mirror reflection taken from 1.6 m above the East River. And the park it should be standing in is not built: the record names **six tiles with no park ground in the 891 m radius** — `t_1_7`, `t_1_8`, `t_1_9`, `t_2_7`, `t_2_8`, `t_2_9` — which is Astoria Park, the place the item's viewpoint names. **0 park-ground meshes, 0 surfaces** in the whole scene. That is J102 at its most visible: the camera stands in one of the city's large waterfront parks and the park is bare terrain.

**There is no facade kit in this frame, and the record's reason for it is worded wrongly.** The kit block reads `placed: 0`, `tiles_missing: []`, `reason: "no kit_placements.bin in range"`. The files are not missing — `tiles_missing` is empty, and every tile in range has both `kit_placements.bin` and `kit_placements.json` on disk. What happened is that **no kit placement record falls inside the kit radius of this camera**: the eye stands on Astoria Park's shore with the nearest buildings far enough out that their facade pieces are beyond it. The distinction matters because the message names the file, which reads as a missing export and is not one. Five sheets in the pass carry this same reason string, all of them bridge or park frames where the camera stands away from any building.

**What the render does contain is a flat pale mass and its reflection**, with a truss gantry across the top, a lamp standard, and a low bar of trees and buildings on the far shore. Measured, the flatness is extreme: standard deviation **0.1006** against the photograph's **0.2093**, a ratio of **0.481**, with a 5th percentile of **0.3026** — almost nothing in the frame is dark. The photograph, by contrast, is a high-contrast summer highway shot with a deep blue sky and hard shadows.

## What matches

* **The refusals are correct and complete.** No fabric at the coordinate, so no height, no extent, no sightline, no lens widening and no tilt — and the record states the distance and bearing to the nearest built thing instead of guessing (J96).
* **The camera was moved off the photograph's GPS for the right reason** — that point is inside the bridge model's own roof, which is what a photograph taken on the bridge looks like to the ground rule (J65).
* **The aim** — recorded azimuth against measured bearing at **0.1°**.
* **Every tile in range has its structures file** — 6 tiles, **0 without a file**, **40,976 triangles**, on a reach carrying the bridge's approach viaducts.
* **Nothing was capped in the props** — **1,621 placed of 1,642 in range**, **0 dropped for budget**, **0 impostor cards dropped**.
* **The fleet is an Astoria fleet** — 25 sedans, 10 SUVs, **2 Sanitation trucks**, 2 yellow taxis, 1 boro taxi, 1 box truck, 1 van, with no buses.

## What does not match

* **The item's coordinate is 90.3 m from any built fabric**, so the sheet measures nothing about the bridge (J96).
* **The reference is a photograph taken from a moving car on the approach**, not a view of the suspension span. Two true views, of two different things.
* **The camera stands 1.6 m above the tidal datum** (J103).
* **Astoria Park has no park ground** — six tiles named, **0 meshes**, **0 surfaces** (J102).
* **There is no facade kit in the frame** — `placed: 0` with `tiles_missing: []`, because no kit placement falls inside the kit radius; the record's reason string says the file is not in range, which is not what happened.
* **Less than half the photograph's contrast** — sd **0.481×** — with a 5th percentile of **0.3026** against **0.1197**.
* **The render is darker at the midtone** — p50 **0.4968** against **0.5937**, a ratio of **0.837**, mean **0.967×**. The photograph's median sits **0.79 stops** above the grey convention and the render's **0.23**, a **−0.56-stop** difference (J83).
* **Two thirds of the photograph's colour** — chroma **0.0993** against **0.1549**, a ratio of **0.641**. The reference's deep blue June sky and its cumulus are most of that.
* **No cloud.** The reference carries a sky full of summer cumulus, which on a frame this open is a large share of the picture; nothing in this build reads a historical sky.
* **The water is a mirror.** No wave state, no turbidity, and at 1.6 m above it that plane is half the frame (J103).
* **Not one tree is drawn from modelled branches** — **0** at LOD0, 1,325 as impostor cards out to 891 m; **515** of them are a substituted species, **9** are scaled outside the allowed band, and the mean scale is **0.848**, the lowest on any sheet written so far.
* **12 props across five kinds in range have no asset** — 4 parks buildings, 3 drinking fountains, 2 memorials, 2 misc structures, 1 parks comfort station. In Astoria Park those are the comfort station and the pool buildings.
* **Sixty-three people in Astoria Park on a June afternoon** — **66 were dropped for standing where the planimetric data has no sidewalk** and 45 for standing in the roadway without crossing, so more were dropped off a walkable surface than were drawn (J101).

## Cause of each gap

| gap | cause | class |
|---|---|---|
| nothing is measurable about the bridge | the item's recorded coordinate stands 90.3 m from the nearest built thing, so the probe found no fabric and the sightline was never tested (J96) | **data — open (J96), the coordinate** |
| the reference is a driver's-eye photograph | the chooser accepted a photograph taken from a car on the bridge; the record then correctly refused to stand on its GPS, because that point is inside the bridge model | **verification — open, the pairing is the fault** |
| the camera stands 1.6 m above the water | the ground sample is unanimous at the tidal datum every tidal body is flattened to (J103) | geometry — open (J103) |
| Astoria Park is bare terrain | six tiles in range have no park ground, and 85 % of the city's mapped open space was never draped (J102) | **data — open (J102)** |
| no facade kit in the frame | no kit placement record falls inside the kit radius of a camera standing on a park shore; the files are all present and `tiles_missing` is empty, and the record's reason string names the file rather than the records | **verification — open, a record wording fault (5 sheets)** |
| sd 0.481, p05 0.3026 | a flat pale mass over a mirror plane, from an eye 1.6 m above the water, against a high-contrast highway photograph (J103) | geometry + verification |
| p50 0.837, chroma 0.641 | the photograph is developed 0.79 stops above the grey convention and the render 0.23 above, and the reference's deep blue sky and cumulus have no counterpart (J83) | reference |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
| 0 trees from modelled branches, mean scale 0.848 | every tree in range is beyond the 120 m modelled-branch radius, and the species lists do not cover this stock (Stage 55, J58's neighbour) | data + performance |
| 12 props across five kinds unmapped | no asset exists for those kinds, the park's comfort station and buildings among them | data |
| 66 people dropped off a walkable surface against 63 drawn | the crowd's walkable test reads only the road network's sidewalk, median, plaza and crosswalk, so a park shore path is unwalkable (J101) | **verification — open (J101)** |
