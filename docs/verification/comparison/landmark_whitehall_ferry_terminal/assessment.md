# Staten Island Ferry Whitehall Terminal

`landmark_whitehall_ferry_terminal` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Staten Island Ferry Whitehall Terminal.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2023-01-17 11:35:59, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Staten_Island_Ferry_Whitehall_Terminal.jpg) — the view direction is derived from the image. It is a close oblique study of the terminal's great glass wall: a raked curtain of green glazing in a steel grid receding steeply up the frame, the concrete base below it and a flat January overcast above.

**Camera** — 40.701808, -74.012939 (NYC_TM -5293, 211) at z 3.3 m NAVD88 | azimuth 200.2°, pitch +0.4° | **24.7 mm** on 36 mm (72.2° horizontal) | 1208x906. The camera stands on **this photograph's own EXIF GPS**, **102.7 m** from the item's recorded viewpoint, whose azimuth it agrees with to **0.2°**. It was then moved **27.6 m** onto the nearest sidewalk polygon: *"boxed in: the view azimuth is closed off 15 m ahead, less than the 24 m this frame needs to show its subject"*, and the walk scored candidates on the subject's own sightline, its chosen point measuring **0.308** — exactly what the sheet published. The move took the subject **further away**, from 47.2 m to **68.0 m**. From there the view is clear for **28.9 m**, nothing built stands within 20 m of the lens, and the nearest simulated body is `agent_veh_camry_black_car_824.46` at **8.9 m** — the black car in the render's near right. The lens is an intermediate focal length rather than a default or the floor, widened from 35 mm only as far as a level axis needed. The record still declares the verticals incomparable with the photograph on proportion. The ground under the lens reads 1.668 m NAVD88, the 10th percentile of 113 samples within 12.0 m, range 1.31 to 3.41 m.

**Sun** — azimuth 172.0°, elevation **28.2°** at 2023-01-17T11:35:59−05:00, from the photograph's own **EXIF DateTimeOriginal**; 753.5 W/m² direct normal, sky at strength 0.0365, Filmic, **+3.07 stops**. Metered on a linear median of **0.021491**, unclamped, against a physical rule of 0.61.

**In the scene** — 4,500,131 triangles: 4 building tiles (42,042 tris), 6 landmark models of which 2 fall inside the 72.2° cone, 16,169 pavement polygons, 1,292 props, 8,734 kit pieces, 12 park-ground meshes, **4 tiles of structures at 107,988 triangles with none lacking a file**, 84 vehicles and 390 people. Seven water bodies, with 10,852 quads on the flattened surface.

## Verdict — the closest tonal agreement of any sheet read this round, and more than half the park ground in the middle distance sits below the terrain

**The terminal is in the frame and it is the right building.** The render's upper half is the glazed wall with its vertical mullions and the steel canopy on triangular brackets running diagonally out of the picture, over a brick-clad base block, which is what the Whitehall Terminal is. The height probe cast 43 rays and **all 43 landed on built fabric**, measuring **24.32 m** above a ground of 2.49 m on `lm_c_whitehall_and_st_george_ferry_terminals.9`, an object **182.4 by 111.1 m** in plan — the terminal's own footprint. The catalogue entry **39.6 m** away carries **27.7 m**, so measured and catalogued agree to **3.4 m**, the difference being the canopy's high edge above the point the ray met.

**The tone is the closest agreement of any sheet read this round.** The render's median sits 0.227 stops from the grey convention and the photograph's 0.31 — a gap of **0.083 stops** — with p50 at **0.974×**, mean at 0.919×, contrast at 0.896× and chroma at 0.837×. All four ratios inside a sixth of unity. A flat January overcast on a glass wall is a scene this build's metered development lands on almost exactly, and it is worth saying that the closest tonal match in a batch of sheets is one whose reference has no direct sun in it at all.

**What the sheet cannot compare is the glass.** The photograph is a few metres from the curtain and its subject is the glazing grid, the panel proportion and the green tint of the glass; the render, after a 27.6 m move that put the subject **21 m further away**, is a street scene at 68 m with a roadway filling its lower half. Four of thirteen rays are clear and four land on the subject, a fraction of **0.308**, with the other nine stopping at **25.6 m** on a bare honeylocust — J88 again, a tree the walk's clearance probe cannot weigh.

**And the park ground in the middle distance is mostly below the terrain.** In the 150 to 400 m band, **0.5382 of 353 samples sit under it** and the **median clearance is −0.067 m** — not a tail of bad samples but a majority, with the middle of the distribution on the wrong side of the ground. Inside 150 m it is clean (339 samples, `under_frac` 0.0, median +0.198 m) and beyond 400 m it is 0.2938 of 160. This is the worst mid-band park-ground reading in the pass, and the Battery's lawns are exactly what sits in that band.

**Structures are the best on any sheet read this round.** Four tiles imported for **107,988 triangles** with **none lacking a file** — the South Ferry loop, the terminal's own structure and the Battery's seawall are all there.

**The budgets bit hard.** More props were dropped than placed: 1,292 drawn against **1,373 dropped** at a 1,348,056-triangle budget, with 920 tree rows among them. And the kit was capped at 1,423,050 triangles and spent windows-first: **8,392 windows against 3 cornices**, with 1,556 pieces suppressed under the landmark shells.

## What matches

* **43 of 43 probe rays on built fabric**, and 24.32 m measured against a catalogued 27.7 m from an entry 39.6 m away — agreeing to 3.4 m on the right object.
* **The closest tonal agreement read this round**: a 0.083-stop exposure gap with p50 0.974×, mean 0.919×, sd 0.896× and chroma 0.837×.
* **The terminal's glazed wall and its canopy are legible** in the render, over the brick base.
* **Structures are complete and substantial**: 4 tiles, **0 without a file**, 107,988 triangles.
* **The camera is the photograph's own GPS** and its heading agrees with the item's own to 0.2°.
* **The lens was widened only as far as it needed**, to 24.7 mm, rather than to the 18 mm floor — one of the few sheets in the pass where an intermediate focal length was chosen.
* **The walk scored on the subject's sightline** and published exactly the fraction its chosen point measured, with no discrepancy (J79, J100).
* **The park ground is clean in the near field**: 339 samples within 150 m, `under_frac` **0.0**, median clearance +0.198 m.
* **The block is furnished for a ferry terminal**: **371 Citi Bike dock units**, **142 benches**, 78 manholes, 73 street lamps, 37 hydrants, 33 waste baskets, 15 vent grates, 13 bus-stop signs, 12 bike racks, **9 flagpoles**, 6 subway entrances and 3 newsstands.
* **121 of the 455 trees are drawn from modelled branches**, and they are correctly bare for 17 January (J97).
* **390 people is a real crowd** for a terminal forecourt, with 376 of them at LOD2.

## What does not match

* **More than half the park ground in the 150 to 400 m band sits below the terrain**: `under_frac` **0.5382** of 353 samples with a **median clearance of −0.067 m** — the worst mid-band reading in the pass, in the band the Battery's lawns occupy.
* **The glass cannot be compared.** The photograph is a few metres from the curtain wall and the render is 68 m away after a move that took it 21 m further from the subject.
* **Nine of thirteen rays stop 25.6 m from the lens on a bare honeylocust** (J88), so the published 0.308 is a tree as much as a terminal.
* **More props were dropped than placed**: 1,292 against **1,373**, including 920 tree rows, at a 1,348,056-triangle budget, with 3 impostor cards dropped as opaque.
* **Three cornices drawn** against 8,392 windows, at a 1,423,050-triangle kit budget, with 1,556 pieces suppressed under the landmark shells.
* **504 pedestrians were dropped for standing in the carriageway without crossing** and 104 for not being on a walkable surface — on a terminal forecourt that is a public plaza the crowd cannot stand on (J101).
* **The verticals converge**, and the record declares the two halves incomparable on proportion.
* **Thirty-nine sedans and twenty-nine SUVs of eighty-four vehicles**, against twelve yellow taxis and one boro taxi, at the Staten Island Ferry's own front door where the taxi rank is the busiest in Lower Manhattan (J105's neighbour: the mix is a draw from the density cell, not a rank).
* **The park ground also sinks beyond 400 m**: 0.2938 of 160 samples, worst case −2.304 m.
* **No cloud, and this reference is all cloud.** The photograph's sky is a flat unbroken January overcast; a Nishita dome at strength 0.0365 has no cloud deck, so the render's shadows are hard where the photograph has none.

## Measured for this assessment

| figure | where it comes from |
|---|---|
| the closest tonal agreement read this round | this sheet's four `render_over_reference` ratios and its 0.083-stop exposure gap, against the forty-eight sheets read in the preceding rounds |
| the worst mid-band park-ground reading in the pass | ranked over every record carrying `parkground.terrain_clearance.bands.mid_150_400m` with at least 100 samples, on `under_frac`; this sheet's 0.5382 with a negative median clearance is the highest |
| the kit total | the sum of this record's `scene.kit.per_category`, which the `total` field does not carry |
| 17 January is inside the leaf-off window | the `leaf_off` rule in `blender/verify/render_sheets.py` (J97) |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| more than half the mid-distance park ground below the terrain | the park surfaces were draped on their own fine grid and this scene's terrain differs from it most in the 150 to 400 m band; the median clearance being negative means the fault is the surface's registration rather than a tail of bad samples (J40, J96) | **verification — open, and the worst instance in the pass** |
| the glass cannot be compared | a close facade reference paired with a frame 68 m away, after a 27.6 m move that increased the distance because the recorded viewpoint was boxed in at 15 m (J79) | verification — declared |
| nine of thirteen rays stop on a tree | the walk's clearance probe tests built fabric and a tree is a prop, so a candidate with a trunk 25 m out scores as clear (J88) | **verification — open** |
| more props dropped than placed | the props triangle budget at 1,348,056 triangles | performance |
| 3 cornices drawn | the kit triangle budget at 1,423,050 triangles, spent windows-first, plus 1,556 pieces suppressed under the landmark shells | performance |
| 504 pedestrians in the carriageway without crossing, 104 off a walkable surface | the terminal forecourt and the Battery's paths are not road-network sidewalk classes, and the placement rules meet a wide roadway the network describes differently from the way it is used (J101) | **verification — open** |
| the fleet is private cars at a ferry rank | the class mix is a draw from the density cell's shares with no rank or stand modelling (J105's neighbour) | data — open |
| no cloud on an all-cloud reference | nothing in this build reads a historical sky, and a Nishita dome has no cloud deck | **reference — no source exists** |
| the verticals converge | the lens was widened only to 24.7 mm and the subject is 24 m tall at 68 m | verification — declared |
