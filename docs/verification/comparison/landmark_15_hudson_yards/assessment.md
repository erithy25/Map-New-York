# 15 Hudson Yards

`landmark_15_hudson_yards` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:15 Hudson Yards 077.jpg by Kidfly182, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0), taken 2025-01-30 13:08:53, 1920x863. [Commons page](https://commons.wikimedia.org/wiki/File:15_Hudson_Yards_077.jpg) — the photograph's own view direction is derived from the image at **medium** confidence. It is the curved glass shaft from directly beneath, filling the entire frame: the four-lobed plan reading as two sweeping curves against a January sky, the spandrel grid stepping away in perspective, and almost nothing else. Its measured chroma is **0.3332**, the highest of any reference in the pass, and its standard deviation **0.137**, among the flattest — a nearly abstract field of blue.

**Camera** — 40.752067, -74.000983 (NYC_TM -4220, 5825) at z 8.0 m NAVD88 | azimuth 310.4°, pitch +27.5° | 18 mm on 36 mm (90.0° horizontal, 48° vertical, landscape) | 1280x576. The camera stands on **the item's recorded viewpoint**, because **this photograph carries no camera GPS**, and the recorded azimuth agrees with the bearing to the subject to **0.0°**. Two things then happened to the eye point, and both are the rules working:

* **It was raised onto a deck.** The record: *the eye point sat **2.65 m under `lm_c_high_line.10`**, the landmark model's own level deck at 9.14 m NAVD88, which stands above the heightmap the eye height was measured from; the camera was raised onto it, so it stands on the surface that is actually drawn under it at **10.74 m NAVD88***. That is J65's deck rule, applied and recorded.
* **It was then walked 95.4 m** onto the nearest surveyed roadbed polygon, the recorded viewpoint being boxed in at **60 m** against the **80.0 m** the frame needs. That is the largest walk offset on any sheet written so far.

From there the view is clear for **96.0 m**, the nearest built thing is `t_-5_5_glass_curtain` **12.0 m** away, and the probe found no simulated agent on its rays across the frame within **20 m** — which is a narrower claim than an empty 20 m disc, though on this sheet the two are close: the scene places **250** pedestrians over a 200 m radius and **77** vehicles over 320 m, so about **3** would fall inside 20 m if they were spread evenly. On the sheets probed to 60 m the same wording hid tens of them, which is why the record's own sentence no longer makes the claim (**DEVIATIONS J120**). The ground reads 6.393 m NAVD88 from the 2 m heightmap, 16 samples within 5 m, range 6.35 to 6.66 m.

**Sun** — azimuth 196.5°, elevation 30.2° at 2025-01-30T13:08:53−05:00, from the photograph's own **EXIF DateTimeOriginal**; 771.9 W/m² direct normal, sky at strength 0.0357, Filmic, **+5.15 stops** metered and unclamped against a linear median of **0.00506** and a target of **0.18**. Declared **under-lit** — beyond hand-held recovery — against a physical rule of **0.51 stops**.

**In the scene** — 3,978,947 triangles: 7 building tiles (235,558 tris, 0 missing, 0 LOD-substituted), 7 landmark models of which 4 can fall inside the 90.0° frame, 30,155 pavement polygons, 2,802 props, 5,491 kit pieces, 19 park-ground meshes, **65,356 triangles of structures**, 77 vehicles and 250 people.

## Verdict — two camera rules worked and the two frames are still of different things

**The deck rule and the walk both did their jobs, visibly.** The eye point began 2.65 m below the High Line's own deck — the classic J65 failure, a camera underground because the heightmap does not know about a raised structure — and was lifted onto the surface actually drawn beneath it. It was then boxed in at 60 m and walked 95.4 m to a roadbed with 96 m of clear view. Both moves are recorded with their distances and their reasons, and the frame that came out is a usable street view rather than a hole in the ground.

**And it is not the photograph's view.** The reference is one tower filling a 1920x863 frame from directly beneath; the render is a 90°-wide upward look holding **three** towers — a blue-glass slab left of centre, a pale shaft behind it, and a tan-and-grey wall with window rows and a lamp standard on the right. The probe measured **281.25 m** above a ground of 6.23 m on `lm_c_hudson_yards.9` — a member presenting **83.6 m** across this camera's bearing of 310.4° and **86.5 m** along it — with **43 of 43** rays on fabric and the height taken from the geometry because the nearest catalogue origin is **193.6 m** away (J74). The fan is that member's own extent and not the **383.2 m** the whole of `lm_c_hudson_yards` presents over **54 parts**, which the record prints beside it and `subject_fan_from` calls "the site rather than the subject" (J113). But of thirteen sightline rays only **2 are clear** and **2 land on the subject**, a visible fraction of **0.154**, the rest stopping at **44.1 m** on a cobra-head lamp; the rays that do get through meet the subject's own fabric at **298.9 m**.

**The measured numbers invert in an instructive way.** The render carries **1.474×** the photograph's contrast and **0.346** of its colour. Both come from the same cause: the reference is a single saturated blue surface and almost nothing else, so it is very colourful and very flat, while the render's 90° frame holds three buildings, a sky, a pavement and a lamp — more range and less colour. Mean **1.073** and p50 **0.972** are close, and the exposure offsets agree to **0.089 stops**, which on an under-lit frame lifted 5.15 stops is worth noting.

**The frustum's cone test is loose here in a way worth seeing.** It lists **The High Line at −96.3° off axis** as inside a **90.0°** frame. The test admits a footprint whose angular span crosses the field of view, and the High Line's span is enormous because it is a 2 km linear park, so a structure entirely behind the camera's shoulder is reported in cone. The record's own note says the test is not a visibility test; this is what that means in practice.

## What matches

* **The deck rule** — the eye point raised 2.65 m onto the High Line's own deck, recorded with both heights (J65).
* **The walk** — boxed in at 60 m, moved 95.4 m to a roadbed with 96 m of clear view, the largest offset in the pass and correctly reported.
* **The height** — 281.25 m on **43 of 43** probe rays, taken from the geometry because the nearest catalogue origin is 193.6 m away (J74).
* **The aim** — recorded azimuth against measured bearing at **0.0°**.
* **The exposure agrees to 0.089 stops**, on a frame lifted 5.15 stops.
* **65,356 triangles of structures** over four tiles — the High Line and the Hudson Yards platform, the second largest structures figure in the pass.
* **Nothing was capped** — props **2,802 of 2,877**, kit **5,491 of 7,197**, **0 dropped for budget**.
* **The High Line is furnished as the High Line** — **101 benches**, 189 Citi Bike units, 103 street lamps, 86 cooling towers, 68 manholes, 46 hydrants, 14 waste baskets.
* **30,155 pavement polygons and none dropped**, including 14,158 white markings, 714 crosswalk and **432 parking-lot**.
* **The park ground is nearly exact near the camera** — within 150 m, 619 samples, an under-fraction of **0.0162** and a median clearance of **0.145 m**.

## What does not match

* **The two frames are of different things** — one tower from beneath against three towers in a 90° frame, at **medium** reference confidence with no GPS to pin it.
* **Two of thirteen rays reach the subject**, the rest stopped by a cobra-head lamp at 44.1 m.
* **Published under-lit at +5.15 stops** against a physical rule of 0.51 (J83).
* **The curved four-lobed shaft is not readable** in the render; the member the probe measured is a box in plan, **83.6 m** across this bearing by **86.5 m** along it.
* **A third of the photograph's colour** — chroma **0.346** — and **1.474×** its contrast, both from the reference being one saturated surface.
* **The frustum reports the High Line at −96.3° off axis inside a 90° frame** (J88).
* **Three of four structure tiles have no file.**
* **No park ground was built for one tile** in range (`t_-6_6`) (J102).
* **967 of the 2,172 trees are a substituted species**, 8 are scaled outside the allowed band, **60** of the 2,095 impostor cards are procedural canopy stems, and 18 props were dropped on a suppressed building.
* **1,706 kit pieces were suppressed** under landmark shells.
* **Beyond 400 m the park ground reads under the terrain on 22 % of 999 samples**, with a worst of **−8.436 m**.
* **3,527 agents were dropped** — 1,077 pedestrians at the agent triangle budget, 263 where the planimetric data has no sidewalk (J101), 219 in the carriageway without crossing, 213 vehicles at the budget, 24 vehicles where there is no roadway, 9 cyclists the fleet exports without a rider.
* **No cloud.** The reference's sky is a thin January haze behind the tower; nothing in this build reads a historical sky.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the two frames are of different things | the photograph carries no GPS, so the item's recorded viewpoint was used and then walked 95.4 m; the chooser accepted the pairing at medium confidence (J104) | **verification — open (J104)** |
| two of thirteen rays reach the subject | one rule-placed cobra-head lamp at 44.1 m blocks the fan from the walked position, which was still the best candidate (J56, J79) | verification + data |
| published under-lit at +5.15 stops | a 90° frame of glass and shadow in a January canyon; the development is metered on it (J83) | verification — declared, and correct |
| the curved shaft is not readable | the member carrying the height is a box in plan, 83.6 m by 86.5 m across and along this bearing; a four-lobed curved envelope is not what the composite's shell models here | geometry |
| chroma 0.346, sd 1.474 | the reference is one saturated blue surface, very colourful and very flat; the render's 90° frame holds three buildings, sky, pavement and a lamp | reference |
| the High Line reported at −96.3° off axis | the frustum admits a footprint whose angular span crosses the field of view, and a 2 km linear park's span is enormous; the record says it is not a visibility test (J88) | verification — cosmetic, and misleading in the record |
| three of four structure tiles without a file | those tiles are unbuilt | data — open |
| no park ground for one tile | 85 % of the city's mapped open space was never draped (J102) | data — open (J102) |
| 967 substituted species, 60 procedural stems | the species lists do not cover this stock and woodland polygons are filled by rule (Stage 55) | data — declared, counted |
| 1,706 kit pieces suppressed | the landmark shell replaces the tile's buildings and takes their kit with it | declared decision |
| a −8.436 m far-field tail | the park builder drapes on its own heightmap and the scene's coarsens at the edge; the redrape closes the near field (J71) | geometry — open, bounded |
| 250 people of 2,312 asked | the agent triangle budget plus the placement rules, each with its own count | performance + verification |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |

## Re-read against the re-rendered record

This sheet was rendered again on the v17 pass's restart, to carry the `record_shape` stamp that
tells a reader which generation of the renderer wrote a record (**DEVIATIONS J119**). Nothing above
was rewritten, and the evidence for leaving it is stronger than a re-reading: diffing the new record
against the committed one field by field, **every measured value is identical**, and the frame it replaced is reproduced **pixel for pixel**: `render.png`'s decoded image is identical, and the only bytes that differ are the five `tEXt` chunks in which Blender records the render date and its own timings. `sheet.png` is byte-identical. What
moved is the wall clock:

`scene.agents.seconds` 786.5 -> 721.12,
`scene.seconds` 977.18 -> 899.06,
`seconds.render` 51.0 -> 63.8,
`seconds.scene` 1104.3 -> 1040.1,
`seconds.total` 1155.3 -> 1103.9.
The other changes are the plan-extent field names, where the object's box moved from
`part_width_m`/`part_narrow_m` to `width_m`/`narrow_m` and the model's from `width_m`/`narrow_m` to
`model_*` (no figure quoted above is a field name), and the wording of the clearance note, where J120 replaced two fallbacks that
claimed an empty disc with sentences that say what the probe measured -- rays across the frame.
Every other field of the clearance reading is unchanged, which is what makes this a rewording of
the same measurement rather than a different one.


## Measured for this assessment

The wall-clock figures in the table below are the **previous** render's, quoted so that "every measured value is identical" is a comparison a reader can check rather than a claim. They were read from this sheet's own `render.json` at commit `837fa93`, its last state before the pass restarted.

| figure | where it comes from |
|---|---|
| 786.5 | `scene.agents.seconds` in the previous record; the re-render took 721.12 s |
| 977.18 | `scene.seconds` in the previous record; the re-render took 899.06 s |
| 51.0 | `seconds.render` in the previous record; the re-render took 63.8 s |
| 1104.3 | `seconds.scene` in the previous record; the re-render took 1040.1 s |
| 1155.3 | `seconds.total` in the previous record; the re-render took 1103.9 s |
