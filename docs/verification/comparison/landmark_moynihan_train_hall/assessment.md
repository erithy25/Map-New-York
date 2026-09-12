# Moynihan Train Hall

`landmark_moynihan_train_hall` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Moynihan Train Hall Upper Level 2026.jpg by Antony-22, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2026-04-21 13:12:22, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Moynihan_Train_Hall_Upper_Level_2026.jpg) — the photograph's own view direction is derived from the image at **high** confidence. **It is an interior photograph**: the skylit hall from the upper level, the barrel vault and its lattice of glazing bars overhead, the platform stair, potted trees, retail frontage and the *9th Avenue* wayfinding sign.

**Camera** — 40.750711, -73.996728 (NYC_TM -3958, 5628) at z 11.4 m NAVD88 | azimuth 70.0°, pitch +5.4° | 35 mm on 36 mm (54.4° horizontal, landscape) | 1208x906. The camera stands on **the item's recorded viewpoint**, not the photograph's: the record states why, and it is the point of this sheet — *this photograph's own EXIF GPS is 129 m away, but the eye point there is inside `lm_c_moynihan_train_hall.1` (a ray straight up from the eye point hits its roof), while the recorded viewpoint is in open air*. The recorded azimuth of 70.0° agrees with the bearing to the subject to **0.1°**. The walk then **moved the camera 12 m backwards**: the recorded viewpoint is boxed in, **closed off 5 m ahead** against the **65.1 m** this frame needs to show its subject, and 12 m back was the nearest point in open air. From there the view is clear for **78.2 m**, the nearest built thing in the frame is **`t_-4_5_concrete` 13.2 m** away and no simulated agent stands within 20 m. The ground under it reads 9.826 m NAVD88, the 10th percentile of 113 samples within 12 m, range 9.39 to 12.12 m.

**Sun** — azimuth 189.0°, elevation 61.0° at 2026-04-21T13:12:22−04:00, from the photograph's own **EXIF DateTimeOriginal**; 921.1 W/m² direct normal, sky at strength 0.0309, Filmic, **+3.79 stops** metered and unclamped, against a linear median of **0.01301** and a target of **0.18**. The physical rule would have given **0.0 stops**.

**In the scene** — 4,500,165 triangles: 4 building tiles (189,114 tris, 0 missing, 0 LOD-substituted), 6 landmark models of which 3 can fall inside the 54.4° frame, 21,773 pavement polygons, 1,610 props, 6,521 kit pieces, 12 park-ground meshes, 40,632 triangles of structures, 88 vehicles and 435 people.

## Verdict — the render is two flat surfaces 13 m from the lens, the subject measures 0 of 13 rays, and the frame gate calls it usable

**There is nothing in the right-hand frame.** A pale concrete plane fills the upper two thirds, a darker grey plane the lower third, and they meet on a diagonal. No building, no street, no kerb, no vehicle, no person, no sky, no horizon. The camera is looking at `t_-4_5_concrete` from **13.2 m** — every concrete surface in that tile joined into one object (J94) — and that single mesh is the picture.

**The record measured this exactly and published the sheet anyway.** `subject_visible` is **false**, `subject_visible_fraction` is **0.0**, **0 of 13** rays are clear, **0** land on the subject, and all of them stop at 13.2 m on that concrete mesh. The frame verdict on the same record reads **`usable: True`**, mean **0.5724**, sd **0.1110**. The gate is `mean ≥ 0.06` and `sd ≥ 0.025` (J69), and a flat wall in sunlight clears both by a wide margin. **The gate tests whether a frame is black or uniform. It has never tested whether the subject is in it**, although the sightline has already measured that before the render starts. This is not a one-off: **19 of the 155 sheets in this pass measure a visible fraction of exactly 0.0, and every one of the 19 is marked usable** — among them the Empire State Building, the Chrysler Building, 40 Wall Street, the Statue of Liberty and the MetLife Building (J100).

## Measured for this assessment

| figure | how |
|---|---|
| 19 sheets of the 155 in the pass at a visible fraction of exactly 0.0, all marked usable | read `sightline.subject_visible_fraction` and `frame.usable` out of every `render.json` that carries `scene.structures`, which is the discriminator for the v16 pass |
| this render's standard deviation is the fifth lowest in the pass and the lowest of any frame meant to contain a building | ranked `frame_stats.json` `render.sd` over the same set: the George Washington Bridge at 0.0919, Hell Gate Bridge at 0.0954, the RFK Triborough Bridge at 0.1006 and the Coney Island Cyclone at 0.1086 are lower, and all four are frames of open sky rather than of a wall |
| the walk's score differs from the rendered measurement on 3 sheets | compared `clearance.subject_sightline_at_choice.subject_visible_fraction` with `sightline.subject_visible_fraction` across the same set |

**The walk also accepted a candidate worse than its own score.** `subject_sightline_at_choice` records the chosen point at **0.077** — one ray of thirteen — and the rendered measurement came out at **0.0**. It is one of only three sheets in the pass where the walk's score at its choice differs from the final measurement, and one of two where the difference is the walk claiming a ray it did not get. There is no floor: a candidate scoring one ray in thirteen is accepted as the best available and rendered, rather than the sheet being declared unrenderable from that viewpoint.

**And the reference should not have been paired with this build at all.** The photograph is of the inside of the train hall, and this build declares no interiors anywhere except volumes visible from the street through glass (B10, I5). The record already holds the evidence in plain words — the eye point at the photograph's own GPS is **inside the model's roof** — and the chooser used the photograph regardless. The two halves of this sheet are not two views of one place; they are a room and a wall.

**The measured statistics say the same thing three ways.** The render's standard deviation, **0.1108**, is the fifth lowest in the pass and the lowest of any frame that is meant to contain a building — the four below it are bridges and a rollercoaster against open sky — and its 5th percentile, **0.4439**, means not one pixel in twenty is even moderately dark — a frame with no shadow, no edge and no depth. Against the photograph: mean **1.561×**, p50 **1.713×**, sd **0.403×**, chroma **1.674×**. Those ratios are not a fidelity reading of anything. The photograph's median sits **1.38 stops below** the grey convention, a dark interior exposed for its skylight, and the render's **0.246 above** it, a **+1.626-stop** difference (J83).

## What matches

Nothing in the picture. What is correct on this sheet is the record's own account of why:

* **The refusal to stand on the photograph's GPS was right.** The eye point there is inside the model, and the record says so rather than rendering from inside a shell.
* **The recorded azimuth agrees with the measured bearing to 0.1°**, so the aim is not at fault.
* **The height probe worked** — **43 of 43** rays on built fabric, **31.41 m** above a ground of 9.85 m, against the catalogue's **31.2 m** for `c_moynihan_train_hall` whose origin stands 71.1 m away. The model's plan extent, **252.6 m by 208.3 m** and not a tile mesh, is the Farley Building's own block.
* **The scene around the camera is fully built** — 4 tiles with **0 missing** and **0 LOD-substituted**, 21,773 pavement polygons with **0 dropped**, **40,632 triangles of structures** (the Penn Station throat runs under this frame), 88 vehicles and **435 people**, all at LOD2, with **0 dropped inside a building** and only 38 off a walkable surface.
* **The props are a Penn Station district's props** — **556 Citi Bike units**, 189 street lamps, 150 manholes, 109 cooling towers, 92 hydrants, **68 benches**, 50 subway vent grates, **17 subway entrances**, 11 bus-stop signs.

## What does not match

* **The subject is not in the frame.** 0 of 13 rays, `subject_visible: false`.
* **The reference is an interior and this build has no interiors** (B10, I5). No barrel vault, no glazing lattice, no platform stair, no retail frontage, no wayfinding.
* **The frame is one tile mesh at 13.2 m.** `t_-4_5_concrete` is every concrete surface in that tile joined into a single object, so the walk could not step past it and the sightline could not see through it (J94).
* **The flattest frame in the pass that is meant to contain a building** — sd **0.1108** against the photograph's **0.2747**, a ratio of **0.403**, with p05 at **0.4439**.
* **The frame gate passed it.** `usable: True` on a frame with no subject in it (J100).
* **The walk accepted 0.077 and rendered 0.0.**
* **Kit was capped to one piece in five** — **6,521 of 33,792 in range** at a **1,226,878-triangle** budget, 6,066 of them windows, and **2,409 further pieces suppressed** under landmark shells.
* **Props were capped** — **1,610 of 2,760 in range** at a **1,243,447-triangle** budget, **954 dropped for budget**, **822** of them tree rows, **22** dropped on a suppressed building; **147** trees are a substituted species and only **14** are drawn from modelled branches against **273** impostor cards.
* **Both tiles in range have no structures file** — 2 imported, **2 without a file** — although 40,632 triangles came from elsewhere in the radius.
* **30 props across six kinds in range have no asset** — 10 vending machines, 9 misc structures, 5 artworks, 3 memorials, 2 drinking fountains, 1 billboard.
* **There is no park ground within 150 m to check** — **0 samples**. Between 150 and 400 m the under-fraction is **0.1474** over 529 samples, worst **−3.49 m**; beyond 400 m **0.2118** over 1,157 samples, worst **−3.865 m**, with a z-fighting fraction of **0.0285**. The redrape moved **77,164** vertices, up to 3.288 m up and 3.503 m down.
* **Four park surface kinds keep the builder's flat colour** — hard sport court, park grass, recreation grass and bare ground (J40).
* **3,585 agents were dropped** — 1,259 pedestrians outside the radius, 1,073 at the agent triangle budget, 656 vehicles outside the radius, 338 vehicles at the budget, 193 pedestrians in the carriageway without crossing, 38 not on a walkable surface, 19 riderless bodies, 9 off the carriageway.
* **The frustum lists Times Square 1,013.8 m away as in-cone** at 26.6° off axis, and Madison Square Garden at 297.8 m — neither is in a frame that contains one wall.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the subject is not in the frame | the recorded viewpoint is boxed in at 5 m against the 65.1 m the frame needs; the walk moved 12 m back, scored its best candidate at 0.077, and the rendered measurement was 0.0 — with no floor below which a candidate is refused (J79, J100) | **verification — open (J100)** |
| the frame is one flat mesh at 13.2 m | `t_-4_5_concrete` is one tile's concrete surfaces joined into a single object, so it cannot be stepped past, seen through, or walked around (J94) | **geometry — open, the join is the fault** |
| the sheet was published as evidence | the frame gate is `mean ≥ 0.06` and `sd ≥ 0.025` and nothing else; a sunlit wall clears both, and the visible fraction the sightline already measured is never consulted (J69, J100) | **verification — open (J100)** |
| the reference is an interior | the chooser paired an interior photograph with a build that declares no interiors, although the record itself records that the photograph's own GPS is inside the model's roof (B10, I5) | **verification — open (J100), and the evidence was already in the record** |
| mean 1.561×, p50 1.713×, sd 0.403× | a dark interior exposed for its skylight, 1.38 stops below the grey convention, against a flat sunlit wall metered to it (J83) — not a reading about the render | reference |
| 6,521 kit pieces of 33,792, and 2,409 more suppressed | the kit triangle budget at 1,226,878, plus the landmark shell replacing the tile's buildings | performance + declared decision |
| 1,610 props of 2,760, 822 tree rows dropped | the props triangle budget at 1,243,447 | performance |
| both tiles without a structures file | those tiles are unbuilt | data — open |
| 30 props across six kinds unmapped | no asset exists for those kinds | data |
| four park surface kinds flat | the texture catalogue has no photographic set for court, grass or bare ground (J40) | data — declared, named on the sheet |
| under-fraction 0.2118 far, worst −3.865 m | the park builder drapes on its own heightmap and the scene's differs; the redrape closes the bulk and leaves that tail (J71) | geometry — open, bounded |
| 435 people of 2,300 asked | the agent triangle budget plus the placement rules, each with its own count | performance + verification |
