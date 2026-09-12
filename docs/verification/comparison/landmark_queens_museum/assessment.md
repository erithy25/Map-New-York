# Queens Museum (New York City Building)

`landmark_queens_museum` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:08132022 WMNYC Wiki Worlds Fair Wikimania Queens Museum.jpg by Wil540 art, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-08-13 17:03:12, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:08132022_WMNYC_Wiki_Worlds_Fair_Wikimania_Queens_Museum.jpg) — the photograph's own view direction is derived from the image at **high** confidence. **It is a photograph of a Wikimedia meetup held inside the museum**: a dozen people in masks, a Wikipedia roll-up banner, folding chairs, a laptop on a trestle table, a red carpet, track lighting on a plasterboard ceiling. Nothing architectural about the building is visible in it except a corridor and a glazed wall.

**Camera** — 40.745464, -73.848006 (NYC_TM 8614, 5054) at z 8.4 m NAVD88 | azimuth 70.0°, pitch +2.7° | 35 mm on 36 mm (54.4° horizontal, landscape) | 1208x906. The camera stands on **the item's recorded viewpoint**, and the record states why in the same words as the Moynihan sheet: *this photograph's own EXIF GPS is 129 m away, but the eye point there is inside `lm_c_flushing_meadows.2` (a ray straight up from the eye point hits its roof), while the recorded viewpoint is in open air*. The recorded azimuth of 70.0° agrees with the bearing to the subject to **0.0°**. The walk **did not move it**: the view azimuth is clear for **89.2 m** against a **60.1 m** requirement, the nearest built thing in the frame is `t_8_5_park_park_ground_grass` **9.0 m** away — a joined park-ground tile mesh (J94) — and no simulated agent stands within 60 m. The ground under it reads 6.841 m NAVD88 from the 2 m heightmap, 16 samples within 5 m, range 5.98 to 7.05 m.

**Sun** — azimuth 261.9°, elevation 31.5° at 2022-08-13T17:03:12−04:00, from the photograph's own **EXIF DateTimeOriginal**; 782.6 W/m² direct normal, sky at strength 0.0354, Filmic, **+0.56 stops** metered and unclamped against a linear median of **0.121758** and a target of **0.18**. The physical rule would have given **0.45 stops** — the two agree to a ninth of a stop, one of the closest agreements in the pass.

**In the scene** — 1,778,880 triangles: 4 building tiles (73,862 tris, 0 missing, 0 LOD-substituted), 3 landmark models of which 2 can fall inside the 54.4° frame, 17,001 pavement polygons, 1,587 props, **33 kit pieces**, 21 park-ground meshes over 498 surfaces, 16,864 triangles of structures, 64 vehicles and **27 people**.

## Verdict — the sheet's statistics compare the outside of a building with the inside of a conference, and the record held the evidence to refuse the pairing

**The render is a good picture of the New York City Building.** The probe found fabric on **43 of 43 rays** and measured **13.6 m** above a ground of 7.26 m on an object **136.5 m by 103.7 m** in plan, not a tile mesh. The nearest catalogue origin is `b_unisphere` at **148.3 m**, **past the 120 m** the old rule looked in, so the height came from the geometry and the record says so (J74) — otherwise this 13.6 m exhibition hall would have been framed as the Unisphere's 42.67 m globe. The frustum agrees with the aim to **0.0°**, twelve of thirteen sightline rays are clear, **twelve land on the subject** for a visible fraction of **0.923**, and eleven of them meet the building's own fabric nearer than the recorded distance, first at 89.2 m. In the frame the museum is what it is: a long low horizontal mass with a regular row of narrow windows, a paved forecourt, two honeylocusts, lamp standards and lawn behind.

**And the left-hand frame is a Wikipedia meetup.** The photograph's own filename says so. There is no facade in it, no massing, no roofline, no material — nothing a comparison sheet can compare. The measured ratios are published anyway: mean **0.904**, standard deviation **0.732**, p50 **0.886**, chroma **0.649**. Every one of those numbers is arithmetic performed on an exhibition hall's exterior against a conference room's interior, and none of them says anything about this build.

**The record could have caught it, and it is the second time.** The same detector that fires on the Moynihan sheet fires here: the photograph's own GPS lies **inside a landmark model's roof**, which for an exterior-only build (B10, I5) is conclusive evidence that the photograph is an interior. The chooser reported it in prose, used the recorded viewpoint instead, and kept the photograph. Two of the sheets written so far are paired with interiors this way (J100).

**One faint thing the render does contain.** A pale sphere outline sits in the sky at the frame's centre, and the frustum accounts for it: the **Unisphere at 268.3 m, 2.8° off axis**, a 42.67 m globe of steel meridians that reads as very nearly transparent against a bright sky. That is arguably correct for an open lattice of tubes; it is also the only thing in the frame a viewer would struggle to name.

## What matches

* **The height, measured off the geometry** — 13.6 m on 43 of 43 rays, because the nearest catalogue origin was 148.3 m away (J74).
* **The aim is exact** — recorded azimuth against measured bearing at **0.0°**, and the frustum's own reading of the subject at the same.
* **The sightline** — 12 of 13 rays clear, 12 on the subject, a visible fraction of **0.923**.
* **The plan** — 136.5 m by 103.7 m, measured off the landmark model.
* **The development is nearly physical** — +0.56 stops metered against 0.45 by the rule.
* **Nothing was capped** — props **1,587 of 1,657 in range**, **0 dropped for budget**.
* **The park ground is exact near the camera** — within 150 m, **387 samples**, an under-fraction of **0.0**, a median clearance of **0.195 m**, a worst of **+0.029 m**, no z-fighting. **1,301 faces** were cut for the landmark's own ground.
* **The Unisphere is in the frame where the frustum says it is.**
* **17,001 pavement polygons and none dropped**, including **764 parking-lot** polygons and 1,587 median, which is what the Grand Central Parkway edge of Flushing Meadows looks like.

## What does not match

* **The reference is a photograph of an event, not of a building.** No part of the sheet's comparison is possible.
* **The four measured ratios are published for a pair that cannot be compared** — mean 0.904, sd 0.732, p50 0.886, chroma 0.649. The photograph's median sits **0.612 stops** above the grey convention and the render's **0.232**, a **−0.38-stop** difference (J83), which here is a fact about two unrelated images.
* **The record detected that the photograph's GPS is inside the model and used the photograph anyway** (J100).
* **Almost no kit was drawn** — **33 pieces of 901 in range**, with **868 suppressed** under landmark shells. 26 windows and 7 doors for a 136 m building.
* **1,094 of the 1,361 trees are a substituted species** — four in five — and 2 are scaled outside the allowed band.
* **145 of the 1,327 impostor cards are procedural canopy stems** placed by rule inside mapped woodland, with inferred species and heights (Stage 55).
* **53 props across five kinds in range have no asset** — **20 parks buildings**, 12 misc structures, 9 drinking fountains, 8 artworks, 4 memorials. Twenty unbuilt parks buildings in Flushing Meadows Corona Park is the largest single unmapped count on any sheet written so far.
* **Twenty-seven people in a public park on an August Saturday afternoon** — the density table asked 292 and 420 were simulated; **89 were dropped for standing where the planimetric data has no sidewalk** and 20 for standing in the roadway without crossing (J101).
* **One of three tiles in range has no structures file.**
* **Eleven park surface kinds keep the builder's flat colour** — infield clay, cemetery grass, golf grass, field grass, greenstreet grass, park grass, hard sport court, pool water, rink ice, recreation grass and bare ground (J40). On a sheet that is mostly park, that is most of the ground.
* **Beyond 400 m the park ground reads under the terrain on 0.235 of 1,230 samples**, worst **−3.498 m**, with a z-fighting fraction of **0.0382**; between 150 and 400 m it is **0.2375** over 379 samples. The redrape moved **346,385** vertices, up to 0.634 m up and 0.803 m down.
* **No cloud.** Nothing in this build reads a historical sky — although on this sheet the reference has no sky in it either.
* **The windows are drawn on the shell, not cut** (Stage 34 / J51).

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the reference is a photograph of a Wikimedia meetup | the chooser paired an interior event photograph with an exterior-only build, although the record itself detected that the photograph's GPS lies inside a landmark model's roof (B10, I5, J100) | **verification — open (J100), and the evidence was already in the record** |
| the measured ratios are meaningless here | they are computed for every sheet regardless of whether the pair is comparable, and nothing gates them on the pairing | **verification — open (J100)** |
| 33 kit pieces of 901 | 868 were suppressed under landmark shells, which is correct behaviour where the landmark model replaces the tile's buildings | declared decision |
| 1,094 of 1,361 trees a substituted species | the species lists do not cover this park's stock and the nearest modelled species is used, counted rather than hidden | data — declared, counted |
| 145 procedural canopy stems | only individually mapped trees exist in the sources, so woodland polygons are filled by rule (Stage 55) | data — declared |
| 53 props across five kinds unmapped, 20 of them parks buildings | no asset exists for those kinds | **data — open, and the largest unmapped count in this batch** |
| 27 people in a park | the crowd's walkable test reads only the road network's sidewalk, median, plaza and crosswalk, so a park path and a lawn are unwalkable (J101) | **verification — open (J101)** |
| the Unisphere reads as a ghost | an open lattice of steel meridians against a bright sky, which is arguably correct and is still the one thing in the frame a viewer cannot name | geometry — arguable |
| a joined park-ground tile mesh 9.0 m from the lens | `t_8_5_park_park_ground_grass` is one tile's park grass joined into a single object (J94) | geometry — open |
| one of three tiles without a structures file | that tile is unbuilt | data — open |
| eleven park surface kinds flat | the texture catalogue has no photographic set for clay, grass, court, pool water, ice or bare ground (J40) | data — declared, named on the sheet |
| under-fraction 0.2375 mid-range, 0.235 far | the terrain grid coarsens to 40 m at the scene edge and the park builder drapes on its own heightmap; the redrape closes the near field to 0.0 and leaves this tail (J71) | geometry — open, bounded |
| windows drawn on the shell | Stage 34 / J51, measured at +48 GB | declared decision — physically impossible here |
