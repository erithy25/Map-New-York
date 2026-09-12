# The Shed

`landmark_the_shed` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Hudson Yards Plaza March 2019 19.jpg by Epicgenius, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2019 — **the year and nothing finer** — 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Hudson_Yards_Plaza_March_2019_19.jpg) — the photograph's own view direction is derived from the image at **medium** confidence. It is the Hudson Yards public square with **the Vessel** filling the middle of the frame, its copper honeycomb of stairs from base to top, The Shed's white telescoping shell at the left edge, 15 and 35 Hudson Yards behind, and a crowd of thirty-odd people on the paving.

**Camera** — 40.753074, -74.00204 (NYC_TM -4395, 5895) at z 8.7 m NAVD88 | azimuth 291.3°, pitch **+42.0°** | 18 mm on 36 mm (90.0° horizontal, 74° vertical, landscape) | 1208x906. The camera stands on **the item's recorded viewpoint**, because **this photograph carries no camera GPS**. The recorded azimuth agrees with the bearing to the subject to **0.0°**. The walk did not move it, and here is the problem: the record says *the view azimuth is clear for **150 m*** and, in the same sentence, *the nearest built thing in the frame is **`prop_lamp_cobra_davit_13` 0.6 m** away*. A lamp standard 60 cm from the lens, at −30° yaw in a 90° frame, is inside the picture and the forward clearance ray never met it. The ground reads 7.051 m NAVD88 from the 2 m heightmap, 16 samples within 5 m, range 6.42 to 7.69 m.

**Sun** — azimuth 284.1°, elevation 20.2° at 2019-06-21T18:30:00−04:00. The instant is **chosen, not measured** (J80): a year-only photograph, 21 June assumed, and 18:30 picked as the hour whose bearing comes within **7°** of the view azimuth. 655.2 W/m² direct normal, Filmic, **+6.00 stops** — **clamped**, and the record's note is the most extreme in the pass: *the frame wanted **+10.99 stops** and was held at +6.00: a scene this far from a photographable level is not developed into a picture of one*. The physical rule would have given **1.11 stops**.

**In the scene** — 3,493,124 triangles: 4 building tiles (189,114 tris, 0 missing, 0 LOD-substituted), 5 landmark models of which 4 can fall inside the 90.0° frame, 19,014 pavement polygons, 1,773 props, 3,177 kit pieces, 12 park-ground meshes, 88 vehicles and 437 people.

## Verdict — aimed 140 m above the ground at a 37 m building, from under a tree, with a lamp post 0.6 m from the lens, and published five stops under

**The aim is wrong by two hundred metres of height, and J94 is why.** The probe found fabric on **43 of 43 rays** and measured **281.4 m** above a ground of 6.08 m on `lm_c_hudson_yards.9`. The Shed is a low building; what stands at its recorded coordinate inside the `c_hudson_yards` composite is a **tower**. The nearest catalogue origin is that composite's own, **169.5 m** away and past the 120 m the old rule looked in, so the height came from the geometry — correctly, by J74's rule, and the geometry was the wrong member. The frame was then pitched **+42.0°** and aimed at *the subject's mid-height, 140.2 m above its ground*, for a building whose roof is a small fraction of that. Everything downstream follows from it.

**The camera is in a thicket and the clearance rule did not notice.** A cobra-head lamp at **0.6 m**, a honeylocust blocking the sightline at **5.3 m**, and the composite's own member `lm_c_hudson_yards.51` at **4.9 m** — all inside a 90° frame whose forward ray is reported clear for 150 m. The published render is what that produces: a tree canopy across the top and right, a dark angular glass mass filling the centre and lower left seen from directly beneath, and one pale sliver of a tower at the upper left. Seven of thirteen sightline rays are "clear" and seven "land on the subject", giving **0.538** — and the fabric they land on is 4.9 m from the lens.

**And the frame is published five stops under.** Even after the +6.00-stop clamp, the render's own median sits **4.997 stops below** the grey convention. The measured ratios are the most extreme in the pass: p50 **0.137**, mean **0.19**, sd **0.434**. A reader should take those as a statement about the camera's position, not about the renderer: the frame is dark because the lens is under a tree pressed against a glass wall at 18:30 with a 20° Sun, and the development refused to invent a picture out of it (J83).

**Nothing of the reference's subject is here.** No Vessel, no telescoping shell, no plaza, no crowd — although 437 people were placed in the scene.

## What matches

* **The aim's bearing** — the recorded azimuth agrees with the measured bearing to **0.0°**, the only exact zero in this batch.
* **The probe is internally correct** — 43 of 43 rays, and the record states plainly that the height came from the geometry rather than the catalogue because the nearest origin was 169.5 m away (J74).
* **The development refused to lift a frame it could not** — clamped at +6.00 from a wanted +10.99, with the reason printed (J83).
* **The reference's own confidence is recorded as medium**, and the sheet bears that out.
* **The plaza is paved** — 19,014 pavement polygons with **0 dropped**, including **369 parking-lot** and 345 crosswalk.
* **151 trees are drawn from modelled branches** within 120 m against 1,007 impostor cards, and 5 of the cards are procedural canopy stems (Stage 55).
* **The park ground is exact near the camera** — within 150 m, 146 samples, 100 % clearing the terrain at a median of **+0.20 m**.

## What does not match

* **The frame is aimed 140.2 m above the ground for a low building**, because the composite member at the Shed's coordinate is a 281.4 m tower (J94).
* **A lamp standard stands 0.6 m from the lens** while the clearance record reports 150 m of clear view (J91).
* **Published five stops under** — the render's own median at **−4.997 stops**, p50 **0.137**, after a +6.00-stop clamp from a wanted +10.99 (J83).
* **No Vessel, no telescoping shell, no plaza, no crowd in the frame.**
* **The instant is chosen, not measured**, so the luminance comparison is not evidence about the render (J80).
* **Two thirds of the photograph's colour** — chroma **0.0485** against **0.0723**, a ratio of **0.671** — which on a frame this dark says little.
* **The reference clips at p95 = 1.0**, so its own highlights are beyond measurement.
* **The openings are drawn on the shells, not cut** (Stage 34 / J51).
* **3,392 agents were dropped** — 931 pedestrians at the agent triangle budget, 240 vehicles at the budget, **221 in the carriageway without crossing**, 74 where the planimetric data has no sidewalk (J101), 19 cyclists the fleet exports without a rider, 16 vehicles where there is no roadway.
* **Beyond 400 m the park ground reads under the terrain on 29 % of 747 samples.**
* **No cloud.** The reference's sky carries March cumulus; nothing in this build reads a historical sky.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| aimed 140.2 m above the ground for a low building | the probe measures the object at the subject's coordinate, and inside the `c_hudson_yards` composite that object is a 281.4 m tower rather than The Shed (J74, J94) | **verification — open (J94), and everything on this sheet follows from it** |
| a lamp post 0.6 m from the lens | the clearance rule tests a forward ray and a frame-wide nearest-obstruction distance, and reports both without reconciling them: 150 m clear along the azimuth, 0.6 m to the nearest built thing at −30° yaw (J91) | **verification — open (J91)** |
| published five stops under | the lens is under a tree against a glass wall at 18:30 with a 20° Sun; the meter asked for +10.99 stops and the clamp refused, with the reason printed (J83) | verification — declared, and correct behaviour |
| no Vessel, shell, plaza or crowd | the frame points up at a tower from 4.9 m away; none of the reference's subject is inside it | verification — a consequence of the aim |
| the instant is chosen | the photograph carries a year and no time (J80) | verification — declared, and the luminance comparison is void |
| openings drawn on the shells | Stage 34 / J51, measured at +48 GB | declared decision — physically impossible here |
| 437 people of 2,385 asked | the agent triangle budget plus the placement rules, each with its own count | performance + verification |
| 29 % of far park-ground samples under the terrain | the park builder drapes on its own heightmap and the scene's coarsens at the edge (J71) | geometry — open, bounded |
| no cloud | nothing in this build reads a historical sky | reference — no source exists |
